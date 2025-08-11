#!/usr/bin/env python3
"""
arXiv 数据导入服务

负责从 arXiv API 获取论文数据并导入到数据库
"""

import datetime as dt
import os
import re
from typing import List, Dict, Any, Optional, Tuple

import feedparser
import pytz
import requests

from backend.db import repo as db_repo


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


def import_arxiv_papers(
    target_date_str: str,
    category: str = "cs.CV",
    limit: Optional[int] = None,
    skip_if_exists: bool = True,
) -> Dict[str, Any]:
    """
    从 arXiv 导入指定日期和分类的论文数据
    
    Args:
        target_date_str: 目标日期 (YYYY-MM-DD)
        category: arXiv 分类 (如 cs.CV)
        limit: 限制导入数量
        skip_if_exists: 是否跳过已存在的论文
        
    Returns:
        Dict: 导入统计信息
    """
    import time
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

    start_time = time.time()
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
    api_time = time.time() - start_time if 'start_time' in locals() else 0
    print(f"⏱️  [导入性能] API调用完成，耗时: {api_time:.2f}s | 返回 {len(feed.entries)} 条")

    filter_start = time.time()
    kept: List[Any] = []
    for i, entry in enumerate(feed.entries):
        pub_utc = dt.datetime(*entry.published_parsed[:6], tzinfo=dt.timezone.utc)
        if start_utc <= pub_utc <= end_utc:
            kept.append(entry)

    filter_time = time.time() - filter_start
    print(f"⏱️  [导入性能] 筛选完成，耗时: {filter_time:.2f}s | 保留 {len(kept)} 条")
    
    if limit is not None:
        kept = kept[:limit]
        print(f"按limit截断为 {len(kept)} 条")
    total = len(kept)

    # ===== 批处理提速路径 =====
    # 1) 预解析 entries，构建待写入行与类别映射
    parse_start = time.time()
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
    parse_time = time.time() - parse_start
    print(f"⏱️  [导入性能] 解析完成，耗时: {parse_time:.2f}s | 处理 {total} 条记录")

    # 2) 处理已存在逻辑
    db_start = time.time()
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
            from backend.db.client import app_schema
            app_schema().from_("papers").upsert(items_for_write, on_conflict="arxiv_id").execute()
            arxiv_to_paper_id.update({r["arxiv_id"]: r["paper_id"] for r in db_repo.get_papers_by_arxiv_ids(all_ids)})

    # 对于已存在的 arxiv，仍需要：
    #  - 更新 update_date 为目标日（确保当天列表统计准确）
    #  - 补建分类关联
    if skip_if_exists and existing_set:
        try:
            from backend.db.client import app_schema
            app_schema().from_("papers").update({"update_date": target_date_str}).in_("arxiv_id", list(existing_set)).execute()
        except Exception as e:
            print(f"轻量更新 existing papers.update_date 失败: {e}")

    # 统一获取 arxiv -> paper_id 映射（包含新写入与已存在）
    try:
        final_rows = db_repo.get_papers_by_arxiv_ids(all_ids)
        arxiv_to_paper_id.update({r["arxiv_id"]: r["paper_id"] for r in final_rows})
    except Exception as e:
        print(f"获取paper映射失败: {e}")

    # 4) 为所有解析的论文建立分类关联（包括已存在但缺少关联的）
    all_category_names: List[str] = []
    for aid in all_ids:
        all_category_names.extend(arxiv_to_categories.get(aid, []))
    cat_name_to_id = db_repo.upsert_categories_bulk(all_category_names) if all_category_names else {}

    # 为所有论文创建关联（upsert机制会自动跳过已存在的关联）
    pairs: List[Tuple[int, int]] = []  # (paper_id, category_id)
    for aid in all_ids:
        pid = arxiv_to_paper_id.get(aid)
        if not pid:
            continue
        for cat in arxiv_to_categories.get(aid, []):
            cid = cat_name_to_id.get(cat)
            if cid:
                pairs.append((pid, cid))
    
    if pairs:
        if items_for_write:
            print(f"⏱️  [导入性能] 为 {len(items_for_write)} 条新论文 + {len(all_ids) - len(items_for_write)} 条已存在论文建立 {len(pairs)} 个分类关联")
        else:
            print(f"⏱️  [导入性能] 为 {len(all_ids)} 条已存在论文补建 {len(pairs)} 个分类关联（可能有重复会被自动跳过）")
        db_repo.upsert_paper_categories_bulk(pairs)
    else:
        print(f"⚡ [导入性能] 无需建立分类关联")
    
    # 5) 计算统计信息
    total_upsert = len(items_for_write)
    total_link = len(pairs)
    
    db_time = time.time() - db_start
    print(f"⏱️  [导入性能] 数据库操作完成，耗时: {db_time:.2f}s | upsert={total_upsert} link={total_link}")
    
    # 优化：仅在调试模式或数量较少时输出详细日志
    if total <= 20 or os.getenv('DEBUG_IMPORT', '').lower() == 'true':
        # 优化：构建 arxiv_id -> parsed_item 的映射，避免重复索引查找
        arxiv_to_item = {r["arxiv_id"]: r for r in parsed_items}
        now = dt.datetime.now().isoformat(timespec='seconds')
        
        # 获取所有解析的论文ID用于日志输出
        all_parsed_ids = {r["arxiv_id"] for r in parsed_items}
        for idx, aid in enumerate(sorted(all_parsed_ids), start=1):
            item = arxiv_to_item.get(aid, {})
            primary_category = item.get("primary_category")
            print(f"[{idx}/{total}] arxiv_id={aid} update_date={target_date_str} search_category={category} now={now}")
            for cat in arxiv_to_categories.get(aid, []):
                cid = cat_name_to_id.get(cat)
                if cid:
                    print(f"    + link category: {cat} (category_id={cid})")
    else:
        print(f"⏭️  [导入性能] 跳过详细日志输出（{total}条记录，如需查看设置 DEBUG_IMPORT=true）")

    return {
        "total_upsert": total_upsert,
        "total_link": total_link,
        "errors": errors,
        "processed": len(kept),
    }


# 向后兼容的别名
import_arxiv_papers_to_db = import_arxiv_papers
