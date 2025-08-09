#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从 arXiv 拉取指定日期/分类的论文并写入 Supabase 数据库：app.papers 与 app.paper_categories。

时间窗口规则：按 ET(US/Eastern) 的 20:00 为每天边界，目标日的窗口为：
  [目标日前一日 20:00, 目标日 20:00] (闭区间)

字段映射：
  - arxiv_id: 例如 "2508.05636v1"（从 entry.id 或 entry.link 的 /abs/<id> 提取，包含版本号）
  - title, authors, abstract, link
  - primary_category: arxiv:primary_category 的 term；无则从 tags 第一项回退
  - update_date: 目标日期（YYYY-MM-DD）
  - ingest_at: 由数据库默认值生成

写库策略：
  - papers: upsert（按 arxiv_id 唯一）
  - categories: 对所有出现的 category term upsert
  - paper_categories: 建立 (paper_id, category_id) 关联（按多对多）

日志：每条写库操作输出到stdout，便于确认。
"""

import datetime as dt
import os
import re
from typing import List, Dict, Any, Optional, Tuple

import feedparser
import pytz
import requests

from db import repo as db_repo


def _extract_arxiv_id(entry: Any) -> Optional[str]:
    """从entry.id或entry.link中提取包含版本号的arXiv ID，如 2508.05636v1。
    规则：优先从 entry.id 中解析 /abs/<id>；否则从 entry.link 解析。
    """
    candidates = []
    if getattr(entry, "id", None):
        candidates.append(entry.id)
    if getattr(entry, "link", None):
        candidates.append(entry.link)

    for url in candidates:
        # 典型: http://arxiv.org/abs/2508.05636v1
        m = re.search(r"/abs/([0-9]{4}\.[0-9]{5}(v\d+)?)(?:[?#].*)?$", url)
        if m:
            return m.group(1)
    # 有些feed可能是https://arxiv.org/abs/YYMM.numberv1 变体，兜底再试一次宽松匹配
    for url in candidates:
        m = re.search(r"([0-9]{4}\.[0-9]{5}v\d+)", url)
        if m:
            return m.group(1)
    return None


def _extract_primary_category(entry: Any) -> Optional[str]:
    # feedparser会把arxiv:primary_category映射到 entry.arxiv_primary_category
    pc = getattr(entry, "arxiv_primary_category", None)
    if isinstance(pc, dict) and pc.get("term"):
        return pc["term"]
    # 回退：从 tags 列表取第一项term
    tags = getattr(entry, "tags", [])
    for t in tags:
        term = t.get("term") if isinstance(t, dict) else None
        if term:
            return term
    return None


def _extract_all_categories(entry: Any) -> List[str]:
    cats: List[str] = []
    tags = getattr(entry, "tags", [])
    for t in tags:
        term = t.get("term") if isinstance(t, dict) else None
        if term and term not in cats:
            cats.append(term)
    # 确保primary也在列表中
    pc = _extract_primary_category(entry)
    if pc and pc not in cats:
        cats.append(pc)
    return cats


def import_arxiv_papers_to_db(
    target_date_str: str,
    category: str = "cs.CV",
    limit: Optional[int] = None,
    skip_if_exists: bool = True,
) -> Dict[str, Any]:
    target_date = dt.datetime.strptime(target_date_str, "%Y-%m-%d").date()
    et_tz = pytz.timezone("US/Eastern")

    start_et = et_tz.localize(dt.datetime.combine(target_date - dt.timedelta(days=1), dt.time(20, 0)))
    end_et = et_tz.localize(dt.datetime.combine(target_date, dt.time(20, 0)))

    start_utc = start_et.astimezone(dt.timezone.utc)
    end_utc = end_et.astimezone(dt.timezone.utc)

    start_date_str = start_utc.strftime("%Y%m%d%H%M%S")
    end_date_str = end_utc.strftime("%Y%m%d%H%M%S")

    base = os.getenv("ARXIV_API_BASE", "https://export.arxiv.org/api/query")
    url = (
        f"{base}?"
        f"search_query=cat:{category}+AND+submittedDate:[{start_date_str}+TO+{end_date_str}]&"
        "sortBy=submittedDate&sortOrder=descending&"
        "max_results=2000"
    )

    print(f"目标日期(ET): {target_date} | 分类: {category}")
    print(f"窗口(ET): {start_et} ~ {end_et}")
    print(f"窗口(UTC): {start_utc} ~ {end_utc}")
    print(f"URL: {url}")

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"requests获取失败，将尝试feedparser直连: {e}")
        try:
            feed = feedparser.parse(url)
        except Exception as e2:
            # 尝试http回退
            http_url = url.replace("https://", "http://")
            print(f"feedparser直连失败，尝试HTTP回退: {e2}")
            feed = feedparser.parse(http_url)
    print(f"API返回 {len(feed.entries)} 条")

    kept: List[Any] = []
    for i, entry in enumerate(feed.entries):
        pub_utc = dt.datetime(*entry.published_parsed[:6], tzinfo=dt.timezone.utc)
        if start_utc <= pub_utc <= end_utc:
            kept.append(entry)

    print(f"筛选后保留 {len(kept)} 条")
    if limit is not None:
        kept = kept[:limit]
        print(f"按limit截断为 {len(kept)} 条")
    total = len(kept)

    # ===== 新：批处理提速路径 =====
    # 1) 预解析 entries，构建待写入行与类别映射
    parsed_items: List[Dict[str, Any]] = []
    arxiv_to_categories: Dict[str, List[str]] = {}
    errors = 0

    for idx, entry in enumerate(kept, start=1):
        try:
            arxiv_id = _extract_arxiv_id(entry)
            if not arxiv_id:
                print(f"[{idx}] 跳过：无法解析arxiv_id | id={getattr(entry, 'id', '')}")
                continue
            title = (entry.title or "").strip().replace("\n", " ")
            authors = ", ".join(a.name for a in getattr(entry, "authors", []) if getattr(a, "name", None))
            abstract = (entry.summary or "").strip().replace("\n", " ")
            link = getattr(entry, "link", f"https://arxiv.org/abs/{arxiv_id}")
            primary_category = _extract_primary_category(entry)
            all_categories = _extract_all_categories(entry)

            upd_time = None
            if getattr(entry, "updated_parsed", None):
                t = dt.datetime(*entry.updated_parsed[:6])  # naive UTC
                upd_time = t.time().isoformat()

            row: Dict[str, Any] = {
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "link": link,
                "update_date": target_date_str,
                "primary_category": primary_category,
            }
            if upd_time:
                row["update_time"] = upd_time

            parsed_items.append(row)
            arxiv_to_categories[arxiv_id] = all_categories
        except Exception as e:
            errors += 1
            print(f"[{idx}] ❌ 预处理失败: {e}")

    total = len(parsed_items)

    # 2) 处理已存在逻辑
    all_ids = [r["arxiv_id"] for r in parsed_items]
    existing_rows = db_repo.get_papers_by_arxiv_ids(all_ids)
    existing_set = {r["arxiv_id"] for r in existing_rows}

    items_for_write: List[Dict[str, Any]]
    if skip_if_exists:
        items_for_write = [r for r in parsed_items if r["arxiv_id"] not in existing_set]
    else:
        items_for_write = parsed_items  # 覆盖更新

    # 3) 批量 upsert/insert papers
    arxiv_to_paper_id: Dict[str, int] = {}
    if items_for_write:
        if skip_if_exists:
            # 仅补缺
            arxiv_to_paper_id.update(db_repo.upsert_papers_bulk(items_for_write))
        else:
            # 覆盖更新：直接 upsert 全量，再查询映射
            from db.client import app_schema
            app_schema().from_("papers").upsert(items_for_write, on_conflict="arxiv_id").execute()
            arxiv_to_paper_id.update({r["arxiv_id"]: r["paper_id"] for r in db_repo.get_papers_by_arxiv_ids(all_ids)})

    # 对于已存在的 arxiv，仍需要：
    #  - 更新 update_date 为目标日（确保当天列表统计准确）
    #  - 补建分类关联
    if skip_if_exists and existing_set:
        try:
            from db.client import app_schema
            app_schema().from_("papers").update({"update_date": target_date_str}).in_("arxiv_id", list(existing_set)).execute()
        except Exception as e:
            print(f"轻量更新 existing papers.update_date 失败: {e}")

    # 统一获取 arxiv -> paper_id 映射（包含新写入与已存在）
    try:
        final_rows = db_repo.get_papers_by_arxiv_ids(all_ids)
        arxiv_to_paper_id.update({r["arxiv_id"]: r["paper_id"] for r in final_rows})
    except Exception as e:
        print(f"获取paper映射失败: {e}")
    # 对于 skip_if_exists=true 的情形，已有的也需要映射（用于后续关联时若你将来想保留，但当前逻辑保持与旧实现一致：跳过已有，不再做关联）

    # 4) 批量 upsert categories 并建立关联（仅对新写入的 paper）
    # 对“当日解析到的全部 arxiv”补建类别关联
    target_arxiv_ids = set(r["arxiv_id"] for r in parsed_items)
    all_category_names: List[str] = []
    for aid in target_arxiv_ids:
        all_category_names.extend(arxiv_to_categories.get(aid, []))
    cat_name_to_id = db_repo.upsert_categories_bulk(all_category_names) if all_category_names else {}

    pairs: List[Tuple[int, int]] = []  # (paper_id, category_id)
    for aid in target_arxiv_ids:
        pid = arxiv_to_paper_id.get(aid)
        if not pid:
            continue
        for cat in arxiv_to_categories.get(aid, []):
            cid = cat_name_to_id.get(cat)
            if cid:
                pairs.append((pid, cid))
    if pairs:
        db_repo.upsert_paper_categories_bulk(pairs)

    # 5) 打印日志（与旧行为尽量一致）
    total_upsert = len(items_for_write)
    total_link = len(pairs)
    for idx, aid in enumerate(sorted(target_arxiv_ids), start=1):
        now = dt.datetime.now().isoformat(timespec='seconds')
        primary_category = parsed_items[[r["arxiv_id"] for r in parsed_items].index(aid)].get("primary_category")
        print(f"[{idx}/{total}] arxiv_id={aid} update_date={target_date_str} search_category={category} now={now}")
        for cat in arxiv_to_categories.get(aid, []):
            cid = cat_name_to_id.get(cat)
            if cid:
                print(f"    + link category: {cat} (category_id={cid})")

    return {
        "total_upsert": total_upsert,
        "total_link": total_link,
        "errors": errors,
        "processed": len(kept),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import arXiv papers into Supabase DB")
    parser.add_argument("date", help="YYYY-MM-DD")
    parser.add_argument("category", help="e.g. cs.CV")
    parser.add_argument("--limit", type=int, default=None, help="process only first N entries")
    args = parser.parse_args()

    stats = import_arxiv_papers_to_db(args.date, args.category, args.limit)
    print("SUMMARY:", stats)


if __name__ == "__main__":
    main()


