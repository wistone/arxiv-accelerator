from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple
import json

from .client import app_schema, get_client


def _ensure_date(value: str | dt.date) -> str:
    if isinstance(value, dt.date):
        return value.isoformat()
    return value


def get_or_create_prompt(prompt_name: str) -> str:
    db = app_schema()
    # Try get
    res = db.from_("prompts").select("prompt_id").eq("prompt_name", prompt_name).limit(1).execute()
    if res.data:
        return res.data[0]["prompt_id"]
    # create empty placeholder; caller can update content later
    db.from_("prompts").insert({"prompt_name": prompt_name, "prompt_content": ""}).execute()
    res = db.from_("prompts").select("prompt_id").eq("prompt_name", prompt_name).limit(1).execute()
    return res.data[0]["prompt_id"]


def upsert_category(category_name: str) -> int:
    db = app_schema()
    # try select
    res = db.from_("categories").select("category_id").eq("category_name", category_name).limit(1).execute()
    if res.data:
        return res.data[0]["category_id"]
    # insert
    db.from_("categories").insert({"category_name": category_name}).execute()
    res = db.from_("categories").select("category_id").eq("category_name", category_name).limit(1).execute()
    return res.data[0]["category_id"]


def upsert_paper(
    *,
    arxiv_id: str,
    title: str,
    authors: str,
    abstract: str,
    link: str,
    update_date: str | dt.date,
    primary_category: Optional[str] = None,
    author_affiliation: Optional[str] = None,
) -> int:
    db = app_schema()
    # check exists
    res = db.from_("papers").select("paper_id").eq("arxiv_id", arxiv_id).limit(1).execute()
    if res.data:
        paper_id = res.data[0]["paper_id"]
        # update lightweight fields (idempotent)
        db.from_("papers").update({
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "link": link,
            "update_date": _ensure_date(update_date),
            "primary_category": primary_category,
            "author_affiliation": author_affiliation,
        }).eq("paper_id", paper_id).execute()
        return paper_id
    # insert
    db.from_("papers").insert({
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "link": link,
        "update_date": _ensure_date(update_date),
        "primary_category": primary_category,
        "author_affiliation": author_affiliation,
    }).execute()
    res = db.from_("papers").select("paper_id").eq("arxiv_id", arxiv_id).limit(1).execute()
    return res.data[0]["paper_id"]


def get_paper_id_by_arxiv_id(arxiv_id: str) -> Optional[int]:
    db = app_schema()
    res = db.from_("papers").select("paper_id").eq("arxiv_id", arxiv_id).limit(1).execute()
    if res.data:
        return res.data[0]["paper_id"]
    return None


def analysis_exists(paper_id: int, prompt_id: str) -> bool:
    db = app_schema()
    res = db.from_("analysis_results").select("analysis_id").eq("paper_id", paper_id).eq("prompt_id", prompt_id).limit(1).execute()
    return bool(res.data)


def update_paper_author_affiliation(paper_id: int, author_affiliation: str) -> None:
    db = app_schema()
    db.from_("papers").update({"author_affiliation": author_affiliation}).eq("paper_id", paper_id).execute()


def link_paper_category(paper_id: int, category_name: str) -> None:
    db = app_schema()
    category_id = upsert_category(category_name)
    # try exists
    res = db.from_("paper_categories").select("paper_id").eq("paper_id", paper_id).eq("category_id", category_id).limit(1).execute()
    if res.data:
        return
    db.from_("paper_categories").insert({"paper_id": paper_id, "category_id": category_id}).execute()


def count_papers_by_date_category(date: str | dt.date, category: str) -> int:
    """快速计数：仅检查papers表中指定日期的论文数量（用于优化搜索性能）"""
    db = app_schema()
    date_str = _ensure_date(date)
    
    try:
        # 🚀 优化：只查papers表，不join categories，大幅提速
        result = (
            db.from_("papers")
            .select("*", count="exact")
            .eq("update_date", date_str)
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


def get_arxiv_ids_from_api(date: str | dt.date, category: str) -> List[str]:
    """轻量级ArXiv API调用：只获取arxiv_id列表（用于智能导入判断）"""
    import feedparser
    import requests
    import datetime as dt
    import pytz
    
    target_date = dt.datetime.strptime(str(date), "%Y-%m-%d").date() if isinstance(date, str) else date
    et_tz = pytz.timezone("US/Eastern")
    
    start_et = et_tz.localize(dt.datetime.combine(target_date - dt.timedelta(days=1), dt.time(20, 0)))
    end_et = et_tz.localize(dt.datetime.combine(target_date, dt.time(20, 0)))
    start_utc = start_et.astimezone(dt.timezone.utc)
    end_utc = end_et.astimezone(dt.timezone.utc)
    
    start_date_str = start_utc.strftime("%Y%m%d%H%M%S")
    end_date_str = end_utc.strftime("%Y%m%d%H%M%S")
    
    url = (
        f"https://export.arxiv.org/api/query?"
        f"search_query=cat:{category}+AND+submittedDate:[{start_date_str}+TO+{end_date_str}]&"
        "sortBy=submittedDate&sortOrder=descending&max_results=2000"
    )
    
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        
        arxiv_ids = []
        for entry in feed.entries:
            # 快速解析ID，不处理其他字段
            import re
            candidates = [getattr(entry, "id", ""), getattr(entry, "link", "")]
            for candidate in candidates:
                m = re.search(r"/abs/([0-9]{4}\.[0-9]{5}(v\d+)?)(?:[?#].*)?$", candidate)
                if m:
                    arxiv_ids.append(m.group(1))
                    break
        
        print(f"[智能导入] ArXiv API返回 {len(arxiv_ids)} 个ID")
        return arxiv_ids
    except Exception as e:
        print(f"[智能导入] ArXiv API调用失败: {e}")
        return []


def get_existing_arxiv_ids_by_date(date: str | dt.date, arxiv_ids: List[str]) -> List[str]:
    """高效检查：指定日期下已存在的arxiv_id列表"""
    if not arxiv_ids:
        return []
    
    db = app_schema()
    date_str = _ensure_date(date)
    
    try:
        # 分批查询，避免IN子句过长
        existing_ids = []
        chunk_size = 100
        for i in range(0, len(arxiv_ids), chunk_size):
            chunk = arxiv_ids[i:i + chunk_size]
            result = (
                db.from_("papers")
                .select("arxiv_id")
                .eq("update_date", date_str)
                .in_("arxiv_id", chunk)
                .execute()
                .data
            )
            existing_ids.extend([r["arxiv_id"] for r in result])
        
        print(f"[智能导入] DB中已存在 {len(existing_ids)}/{len(arxiv_ids)} 个ID")
        return existing_ids
    except Exception as e:
        print(f"[智能导入] DB检查失败: {e}")
        return []


def smart_check_and_read(date: str | dt.date, category: str, arxiv_ids: List[str]) -> Dict[str, Any]:
    """🚀 一体化操作：检查存在性+读取完整数据，避免两次DB查询
    
    修复：分两步检查
    1. 检查论文是否在数据库中存在（按date+arxiv_id）
    2. 检查是否已建立该分类关联，如果没有则需要补建
    """
    import time
    
    if not arxiv_ids:
        return {'existing_ids': [], 'articles': []}
    
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    
    try:
        print(f"[一体化] 开始联合查询：存在性检查+完整数据读取")
        start_time = time.time()
        
        # 🔧 修复：第一步，检查该日期下所有已存在的论文（不限分类关联）
        all_existing_papers = []
        chunk_size = 100
        for i in range(0, len(arxiv_ids), chunk_size):
            chunk = arxiv_ids[i:i + chunk_size]
            
            # 查询该日期下所有已存在的论文
            papers_result = (
                db.from_("papers")
                .select("paper_id, arxiv_id, title, authors, abstract, link, author_affiliation")
                .eq("update_date", date_str)
                .in_("arxiv_id", chunk)
                .order("arxiv_id", desc=True)
                .execute()
                .data
            )
            all_existing_papers.extend(papers_result)
        
        existing_paper_ids = [p["paper_id"] for p in all_existing_papers]
        existing_arxiv_ids = [p["arxiv_id"] for p in all_existing_papers]
        
        # 🔧 修复：第二步，检查哪些论文已经建立了该分类关联
        linked_paper_ids = []
        if existing_paper_ids:
            for i in range(0, len(existing_paper_ids), chunk_size):
                chunk_ids = existing_paper_ids[i:i + chunk_size]
                linked_result = (
                    db.from_("paper_categories")
                    .select("paper_id")
                    .eq("category_id", category_id)
                    .in_("paper_id", chunk_ids)
                    .execute()
                    .data
                )
                linked_paper_ids.extend([r["paper_id"] for r in linked_result])
        
        # 找出已建立分类关联的论文数据
        linked_papers = [p for p in all_existing_papers if p["paper_id"] in linked_paper_ids]
        
        query_time = time.time() - start_time
        print(f"[一体化] 联合查询完成，耗时: {query_time:.2f}s | 该日期已有 {len(existing_arxiv_ids)} 条，该分类下已关联 {len(linked_papers)} 条")
        
        # 转换为前端格式（只返回已建立分类关联的论文）
        articles = []
        for idx, r in enumerate(linked_papers, start=1):
            articles.append({
                "number": idx,
                "id": r["arxiv_id"],
                "title": r["title"],
                "authors": r.get("authors") or "",
                "abstract": r.get("abstract") or "",
                "link": r.get("link") or "",
                "author_affiliation": r.get("author_affiliation") or "",
            })
        
        return {
            'existing_ids': existing_arxiv_ids,  # 🔧 返回所有已存在的论文ID（用于导入判断）
            'articles': articles,  # 🔧 返回已建立分类关联的论文（用于前端显示）
            'query_time': query_time
        }
        
    except Exception as e:
        print(f"[一体化] 联合查询失败: {e}")
        return {'existing_ids': [], 'articles': []}


def list_papers_by_date_category(date: str | dt.date, category: str) -> List[Dict[str, Any]]:
    db = app_schema()
    date_str = _ensure_date(date)
    # 优先走一次请求的内联JOIN查询（通过外键自动关系），显著减少网络往返
    category_id = upsert_category(category)
    try:
        # 使用range替代limit以避免Supabase的默认限制
        joined_rows = (
            db.from_("paper_categories")
            .select("papers!inner(paper_id, arxiv_id, title, authors, abstract, link, author_affiliation)")
            .eq("category_id", category_id)
            .eq("papers.update_date", date_str)
            .order("arxiv_id", foreign_table="papers", desc=True)
            .range(0, 4999)  # 获取前5000条记录
            .execute()
            .data
        )
        rows: List[Dict[str, Any]] = []
        for r in joined_rows:
            p = r.get("papers") or {}
            if p:
                rows.append(p)
        # 调试日志
        try:
            print(f"[repo] fast-join rows for date={date_str}, category={category}: {len(rows)}")
        except Exception:
            pass
    except Exception as _join_err:
        # 回退方案：分页取关联 + 分块查papers（较慢，但保证可用）
        ids: List[int] = []
        page_size = 500
        offset = 0
        while True:
            q_link = (
                db.from_("paper_categories")
                .select("paper_id")
                .eq("category_id", category_id)
            )
            batch = q_link.range(offset, offset + page_size - 1).execute().data
            if not batch:
                break
            ids.extend([row["paper_id"] for row in batch])
            offset += page_size
            if len(batch) < page_size:
                break
        if not ids:
            return []
        rows = []
        chunk_size = 500
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i:i + chunk_size]
            q_papers = (
                db.from_("papers")
                .select("paper_id, arxiv_id, title, authors, abstract, link, author_affiliation")
                .in_("paper_id", chunk)
                .eq("update_date", date_str)
                .order("arxiv_id", desc=True)
            )
            part = q_papers.range(0, len(chunk) - 1).execute().data
            rows.extend(part)
        try:
            print(f"[repo] fallback rows for date={date_str}, category={category}: {len(rows)}")
        except Exception:
            pass
    # map to legacy articles structure
    articles: List[Dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        articles.append({
            "number": idx,
            "id": r["arxiv_id"],
            "title": r["title"],
            "authors": r.get("authors") or "",
            "abstract": r.get("abstract") or "",
            "link": r.get("link") or "",
            "author_affiliation": r.get("author_affiliation") or "",
        })
    return articles


def get_prompt_id_by_name(prompt_name: str = "system_default") -> Optional[str]:
    db = app_schema()
    res = db.from_("prompts").select("prompt_id").eq("prompt_name", prompt_name).limit(1).execute()
    if res.data:
        return res.data[0]["prompt_id"]
    return None


def list_unanalyzed_papers(date: str | dt.date, category: str, prompt_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    db = app_schema()
    date_str = _ensure_date(date)
    # paper ids by category - 使用分页避免截断
    category_id = upsert_category(category)
    paper_ids = []
    page_size = 1000
    offset = 0
    while True:
        rows = (
            db.from_("paper_categories")
            .select("paper_id")
            .eq("category_id", category_id)
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        if not rows:
            break
        paper_ids.extend([r["paper_id"] for r in rows])
        offset += page_size
        if len(rows) < page_size:
            break
    
    if not paper_ids:
        return []

    # already analyzed for this prompt - 分块查询
    analyzed_ids = set()
    chunk_size = 50
    for i in range(0, len(paper_ids), chunk_size):
        chunk_ids = paper_ids[i:i + chunk_size]
        chunk_rows = (
            db.from_("analysis_results")
            .select("paper_id")
            .eq("prompt_id", prompt_id)
            .in_("paper_id", chunk_ids)
            .execute()
            .data
        )
        analyzed_ids.update(r["paper_id"] for r in chunk_rows)

    # candidate papers (by date) - 分块查询
    candidates = []
    for i in range(0, len(paper_ids), chunk_size):
        chunk_ids = paper_ids[i:i + chunk_size]
        chunk_candidates = (
            db.from_("papers")
            .select("paper_id, arxiv_id, title, authors, abstract, link, author_affiliation")
            .eq("update_date", date_str)
            .in_("paper_id", chunk_ids)
            .order("arxiv_id")
            .execute()
            .data
        )
        candidates.extend(chunk_candidates)

    pending = [r for r in candidates if r["paper_id"] not in analyzed_ids]
    if limit:
        pending = pending[:limit]
    return pending


def insert_analysis_result(
    *, paper_id: int, prompt_id: str, analysis_json: Dict[str, Any], created_by: Optional[str]
) -> Optional[int]:
    db = app_schema()
    try:
        db.from_("analysis_results").insert({
            "paper_id": paper_id,
            "prompt_id": prompt_id,
            "analysis_result": analysis_json,
            "created_by": created_by,
        }).execute()
        # fetch id
        res = db.from_("analysis_results").select("analysis_id").eq("paper_id", paper_id).eq("prompt_id", prompt_id).limit(1).execute()
        if res.data:
            return res.data[0]["analysis_id"]
        return None
    except Exception:
        # likely unique violation (paper_id, prompt_id) → ignore
        return None


def get_analysis_results(
    *, date: str | dt.date, category: str, prompt_id: str, limit: Optional[int] = None, order_by: str = "arxiv_id.asc"
) -> List[Dict[str, Any]]:
    """按“当天 + 分类 + prompt”返回分析结果。

    - 仅返回当天该分类的论文分析（不会混入其它日期）
    - 元数据从 papers 表取（title/authors/abstract/link/author_affiliation）
    - 顺序与搜索页一致（按 arxiv_id 升序）
    - limit 若提供，则在最终顺序上截断
    """
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)

    # 1) 取当天+分类的 papers 列表（保持顺序）
    #    先取该分类下全部 paper_id（分页防止截断）
    all_category_paper_ids: List[int] = []
    page_size = 1000
    offset = 0
    while True:
        rows = (
            db.from_("paper_categories").select("paper_id").eq("category_id", category_id)
            .range(offset, offset + page_size - 1).execute().data
        )
        if not rows:
            break
        all_category_paper_ids.extend([r["paper_id"] for r in rows])
        offset += page_size
        if len(rows) < page_size:
            break
    if not all_category_paper_ids:
        return []

    # 当天该分类的 papers（保序）
    papers_rows: List[Dict[str, Any]] = []
    # 分块避免 in() 过长
    chunk = 1000
    temp_rows: List[Dict[str, Any]] = []
    for i in range(0, len(all_category_paper_ids), chunk):
        part_ids = all_category_paper_ids[i:i + chunk]
        part = (
            db.from_("papers")
            .select("paper_id, arxiv_id, title, authors, abstract, link, author_affiliation")
            .eq("update_date", date_str)
            .in_("paper_id", part_ids)
            .order("arxiv_id")
            .execute().data
        )
        temp_rows.extend(part)
    # 可能顺序已按 arxiv_id；为稳妥，统一再排一次
    # 搜索页按 arxiv_id 降序（最新编号靠前），保持一致
    papers_rows = sorted(temp_rows, key=lambda r: r.get("arxiv_id", ""), reverse=True)
    if not papers_rows:
        return []

    date_paper_ids_ordered = [r["paper_id"] for r in papers_rows]

    # 2) 读取该 prompt 的 analysis 结果（仅当天papers）→ 建映射
    analyzed_map: Dict[int, Dict[str, Any]] = {}
    # 分页读取 analysis_results，避免默认分页
    offset = 0
    page_size = 1000
    id_set = set(date_paper_ids_ordered)
    while True:
        rows = (
            db.from_("analysis_results")
            .select("paper_id, analysis_result, norm_score")
            .eq("prompt_id", prompt_id)
            .range(offset, offset + page_size - 1)
            .order("norm_score", desc=True)
            .execute().data
        )
        if not rows:
            break
        for r in rows:
            pid = r.get("paper_id")
            if pid in id_set and pid not in analyzed_map:
                analyzed_map[pid] = r
        offset += page_size
        if len(rows) < page_size:
            break

    # 3) 组装输出：按 papers_rows 顺序，仅包含已分析的；应用 limit
    articles: List[Dict[str, Any]] = []
    for idx, p in enumerate(papers_rows, start=1):
        row = analyzed_map.get(p["paper_id"])  # 若无分析则跳过
        if not row:
            continue
        articles.append({
            "number": len(articles) + 1,
            "paper_id": p.get("paper_id"),
            "analysis_result": json.dumps(row["analysis_result"], ensure_ascii=False, separators=(",", ":")),
            "title": p.get("title", ""),
            "authors": p.get("authors", ""),
            "abstract": p.get("abstract", ""),
            "link": p.get("link", ""),
            "author_affiliation": p.get("author_affiliation", ""),
        })
        if limit and len(articles) >= limit:
            break
    return articles


def get_analysis_status(date: str | dt.date, category: str, prompt_id: str) -> Dict[str, int]:
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    # 所有该分类下的 paper_id
    # 需要分页抓取，避免默认只返回10条
    all_category_paper_ids: List[int] = []
    page_size = 1000
    offset = 0
    while True:
        rows = (
            db.from_("paper_categories")
            .select("paper_id")
            .eq("category_id", category_id)
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        if not rows:
            break
        all_category_paper_ids.extend([r["paper_id"] for r in rows])
        offset += page_size
        if len(rows) < page_size:
            break
    if not all_category_paper_ids:
        return {"total": 0, "completed": 0, "pending": 0}
    # 该日期 + 该分类的 paper_id 集合
    # 分块查询以避免in()参数过多的限制
    date_paper_ids = []
    chunk_size = 50  # 每次查询50个ID
    for i in range(0, len(all_category_paper_ids), chunk_size):
        chunk_ids = all_category_paper_ids[i:i + chunk_size]
        chunk_rows = (
            db.from_("papers")
            .select("paper_id")
            .eq("update_date", date_str)
            .in_("paper_id", chunk_ids)
            .execute()
            .data
        )
        date_paper_ids.extend([r["paper_id"] for r in chunk_rows])
    total = len(date_paper_ids)
    if total == 0:
        return {"total": 0, "completed": 0, "pending": 0}
    # 已完成（仅统计该日期集合）
    # 分块查询以避免in()参数过多的限制
    completed_paper_ids = []
    chunk_size = 50  # 每次查询50个ID
    for i in range(0, len(date_paper_ids), chunk_size):
        chunk_ids = date_paper_ids[i:i + chunk_size]
        chunk_rows = (
            db.from_("analysis_results")
            .select("paper_id")
            .eq("prompt_id", prompt_id)
            .in_("paper_id", chunk_ids)
            .execute()
            .data
        )
        completed_paper_ids.extend([r["paper_id"] for r in chunk_rows])
    completed = len(completed_paper_ids)
    pending = max(total - completed, 0)
    return {"total": total, "completed": completed, "pending": pending}


def list_available_dates() -> List[str]:
    """Return distinct update_date values (as ISO strings) sorted desc."""
    db = app_schema()
    rows = db.from_("papers").select("update_date").order("update_date", desc=True).execute().data
    seen: set[str] = set()
    result: List[str] = []
    for r in rows:
        d = r.get("update_date")
        if not d:
            continue
        # supabase returns 'YYYY-MM-DD' string for date
        if d not in seen:
            seen.add(d)
            result.append(d)
    return result


# =====================
# 批量写入/查询 加速接口
# =====================

def get_papers_by_arxiv_ids(arxiv_ids: List[str]) -> List[Dict[str, Any]]:
    db = app_schema()
    if not arxiv_ids:
        return []
    # PostgREST in() 最多参数可能有限制，做一下分块
    result: List[Dict[str, Any]] = []
    chunk_size = 500
    for i in range(0, len(arxiv_ids), chunk_size):
        chunk = arxiv_ids[i:i + chunk_size]
        rows = (
            db.from_("papers")
            .select("paper_id, arxiv_id")
            .in_("arxiv_id", chunk)
            .execute()
            .data
        )
        result.extend(rows)
    return result


def upsert_papers_bulk(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """批量 upsert papers，返回 arxiv_id -> paper_id 的映射。

    策略：
      1) 先查已有 arxiv_id → paper_id（一次或分块）
      2) 仅对缺失的执行批量 upsert/insert（带 returning），再整体 select 一次获得完整映射
    """
    import time
    db = app_schema()
    if not rows:
        return {}

    all_arxiv_ids = [r["arxiv_id"] for r in rows if r.get("arxiv_id")]
    existing = get_papers_by_arxiv_ids(all_arxiv_ids)
    arxiv_to_id: Dict[str, int] = {r["arxiv_id"]: r["paper_id"] for r in existing}

    missing_rows = [r for r in rows if r["arxiv_id"] not in arxiv_to_id]
    if missing_rows:
        # 🚀 对大量论文进行分块处理，避免单次请求过大
        chunk_size = 50  # 减小论文写入的分块大小
        
        if len(missing_rows) > chunk_size:
            print(f"[论文写入] 分块处理 {len(missing_rows)} 条新论文")
        
        for i in range(0, len(missing_rows), chunk_size):
            chunk = missing_rows[i:i + chunk_size]
            chunk_start = time.time()
            
            # 添加重试机制
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    db.from_("papers").upsert(chunk, on_conflict="arxiv_id").execute()
                    break
                except Exception as e:
                    retry_count += 1
                    if "Connection reset by peer" in str(e) and retry_count < max_retries:
                        print(f"[论文写入] 块 {i//chunk_size + 1} 连接重置，重试 {retry_count}/{max_retries}")
                        time.sleep(2)
                        continue
                    elif retry_count >= max_retries:
                        # 最后尝试使用insert
                        try:
                            db.from_("papers").insert(chunk).execute()
                            break
                        except Exception:
                            raise e
                    else:
                        raise e
            
            chunk_time = time.time() - chunk_start
            if chunk_time > 3:
                print(f"[论文写入] 块 {i//chunk_size + 1} 完成，耗时: {chunk_time:.2f}s")

    # 统一再 select 一次，得到完整映射
    final_rows = get_papers_by_arxiv_ids(all_arxiv_ids)
    final_map: Dict[str, int] = {r["arxiv_id"]: r["paper_id"] for r in final_rows}
    return final_map


def get_categories_by_names(names: List[str]) -> List[Dict[str, Any]]:
    db = app_schema()
    if not names:
        return []
    result: List[Dict[str, Any]] = []
    chunk_size = 1000
    for i in range(0, len(names), chunk_size):
        chunk = names[i:i + chunk_size]
        rows = (
            db.from_("categories")
            .select("category_id, category_name")
            .in_("category_name", chunk)
            .execute()
            .data
        )
        result.extend(rows)
    return result


def upsert_categories_bulk(names: List[str]) -> Dict[str, int]:
    db = app_schema()
    if not names:
        return {}
    uniq = sorted({n for n in names if n})
    existing = get_categories_by_names(uniq)
    name_to_id: Dict[str, int] = {r["category_name"]: r["category_id"] for r in existing}

    missing = [n for n in uniq if n not in name_to_id]
    if missing:
        rows = [{"category_name": n} for n in missing]
        try:
            db.from_("categories").upsert(rows, on_conflict="category_name").execute()
        except Exception:
            db.from_("categories").insert(rows).execute()

    # fetch all
    final_rows = get_categories_by_names(uniq)
    final_map: Dict[str, int] = {r["category_name"]: r["category_id"] for r in final_rows}
    return final_map


def upsert_paper_categories_bulk(pairs: List[Tuple[int, int]]) -> None:
    """批量 upsert paper_categories，pairs 为 (paper_id, category_id)。"""
    import time
    db = app_schema()
    if not pairs:
        return
    rows = [{"paper_id": p, "category_id": c} for p, c in pairs]
    
    # 🚀 优化：对大量关联进行分块处理，避免单次请求过大
    chunk_size = 100  # 进一步减小分块，避免超时
    total_chunks = (len(rows) + chunk_size - 1) // chunk_size
    
    if len(rows) > chunk_size:
        print(f"[批处理] 分 {total_chunks} 块处理 {len(rows)} 个分类关联")
    
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        chunk_start = time.time()
        try:
            # 添加超时重试机制
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    db.from_("paper_categories").upsert(chunk, on_conflict="paper_id,category_id").execute()
                    break
                except Exception as e:
                    retry_count += 1
                    if "Connection reset by peer" in str(e) and retry_count < max_retries:
                        print(f"[批处理] 块 {i//chunk_size + 1} 连接重置，重试 {retry_count}/{max_retries}")
                        time.sleep(2)  # 等待2秒后重试
                        continue
                    else:
                        raise e
            
            chunk_time = time.time() - chunk_start
            if chunk_time > 5:  # 如果单块耗时超过5秒，记录日志
                print(f"[批处理] 块 {i//chunk_size + 1}/{total_chunks} 完成，耗时: {chunk_time:.2f}s")
                
        except Exception as e:
            # 退化：逐条插入，遇到重复则忽略
            print(f"[批处理] 块 {i//chunk_size + 1} upsert失败，退化为逐条插入: {e}")
            for row in chunk:
                try:
                    db.from_("paper_categories").insert([row]).execute()
                except Exception:
                    # 忽略重复错误
                    pass


def list_existing_analyses_for_prompt(paper_ids: List[int], prompt_id: str) -> List[int]:
    """返回已存在分析结果的 paper_id 列表（指定 prompt）。"""
    db = app_schema()
    if not paper_ids:
        return []
    result: List[int] = []
    chunk_size = 1000
    for i in range(0, len(paper_ids), chunk_size):
        chunk = paper_ids[i:i + chunk_size]
        rows = (
            db.from_("analysis_results")
            .select("paper_id")
            .eq("prompt_id", prompt_id)
            .in_("paper_id", chunk)
            .execute()
            .data
        )
        result.extend([r["paper_id"] for r in rows])
    return result


def insert_analysis_results_bulk(rows: List[Dict[str, Any]]) -> None:
    """批量 upsert analysis_results（按 unique (paper_id, prompt_id)）。"""
    db = app_schema()
    if not rows:
        return
    try:
        db.from_("analysis_results").upsert(rows, on_conflict="paper_id,prompt_id").execute()
    except Exception:
        # 退化为分块 insert，遇到重复由唯一键保护
        chunk_size = 1000
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i + chunk_size]
            try:
                db.from_("analysis_results").insert(chunk).execute()
            except Exception:
                # 忽略重复错误
                pass

