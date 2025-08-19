from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple
import json
import time

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


def list_papers_by_date_category_reliable(date: str | dt.date, category: str) -> List[Dict[str, Any]]:
    """
    可靠版本：使用分步查询确保不会丢失数据
    1. 先获取所有该分类的paper_id（分页）
    2. 再查询指定日期的papers（分块）
    """
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    
    print(f"[repo-reliable] 开始查询 date={date_str}, category={category}")
    
    # 1. 获取该分类的所有paper_id（分页避免截断）
    all_paper_ids = []
    page_size = 1000
    offset = 0
    while True:
        batch = (
            db.from_("paper_categories")
            .select("paper_id")
            .eq("category_id", category_id)
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        if not batch:
            break
        all_paper_ids.extend([r["paper_id"] for r in batch])
        offset += page_size
        if len(batch) < page_size:
            break
    
    print(f"[repo-reliable] 该分类总paper_id数: {len(all_paper_ids)}")
    
    # 2. 分块查询指定日期的papers
    papers = []
    chunk_size = 500
    for i in range(0, len(all_paper_ids), chunk_size):
        chunk_ids = all_paper_ids[i:i + chunk_size]
        chunk_papers = (
            db.from_("papers")
            .select("paper_id, arxiv_id, title, authors, abstract, link, author_affiliation")
            .in_("paper_id", chunk_ids)
            .eq("update_date", date_str)
            .order("arxiv_id", desc=True)
            .execute()
            .data
        )
        papers.extend(chunk_papers)
    
    print(f"[repo-reliable] 指定日期的论文数: {len(papers)}")
    
    # 3. 转换为articles格式
    articles = []
    for idx, paper in enumerate(papers, start=1):
        articles.append({
            "number": idx,
            "id": paper["arxiv_id"],
            "title": paper["title"],
            "authors": paper.get("authors") or "",
            "abstract": paper.get("abstract") or "",
            "link": paper.get("link") or "",
            "author_affiliation": paper.get("author_affiliation") or "",
        })
    
    return articles

def list_papers_by_date_category(date: str | dt.date, category: str) -> List[Dict[str, Any]]:
    db = app_schema()
    date_str = _ensure_date(date)
    # 优先走一次请求的内联JOIN查询（通过外键自动关系），显著减少网络往返
    category_id = upsert_category(category)
    try:
        # 使用range替代limit以避免Supabase的默认限制，并增加更大的范围
        joined_rows = (
            db.from_("paper_categories")
            .select("papers!inner(paper_id, arxiv_id, title, authors, abstract, link, author_affiliation)")
            .eq("category_id", category_id)
            .eq("papers.update_date", date_str)
            .order("arxiv_id", foreign_table="papers", desc=True)
            .range(0, 9999)  # 增加到10000条记录，确保不会截断
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
            print(f"[repo] joined_rows原始数量: {len(joined_rows)}, 过滤后的rows数量: {len(rows)}")
            if len(joined_rows) != len(rows):
                print(f"[repo] 注意：joined_rows和rows数量不一致，可能存在空papers字段")
            
            # 如果返回的数据看起来被截断了（比如正好是5000或10000），或者数量显著偏少，使用可靠版本
            if len(rows) in [5000, 10000]:
                print(f"[repo] 检测到可能的截断（{len(rows)}条），切换到可靠版本")
                return list_papers_by_date_category_reliable(date, category)
            
            # 如果JOIN查询的结果明显少于预期（比如只有129条但实际应该有132条），也切换到可靠版本
            if len(joined_rows) > 0 and len(rows) != len(joined_rows):
                print(f"[repo] JOIN结果不一致（原始{len(joined_rows)}，过滤后{len(rows)}），切换到可靠版本")
                return list_papers_by_date_category_reliable(date, category)
                
        except Exception:
            pass
    except Exception as _join_err:
        # 回退方案：使用可靠版本
        print(f"[repo] JOIN查询失败，使用可靠版本: {_join_err}")
        return list_papers_by_date_category_reliable(date, category)
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


def get_prompt_content_by_name(prompt_name: str = "multi-modal-llm") -> Optional[str]:
    """根据提示词名称获取内容。"""
    db = app_schema()
    res = db.from_("prompts").select("prompt_content").eq("prompt_name", prompt_name).limit(1).execute()
    if res.data:
        return res.data[0]["prompt_content"]
    return None


def get_system_prompt() -> str:
    """获取系统分析提示词（优先从数据库读取，回退到文件）。"""
    # 优先从数据库读取 multi-modal-llm prompt
    db_prompt = get_prompt_content_by_name("multi-modal-llm")
    if db_prompt:
        print("📋 [提示词] 从数据库读取 multi-modal-llm 提示词")
        return db_prompt
    
    # 回退方案：从文件读取（兼容旧版本）
    import os
    fallback_file = "prompt/multi-modal-llm-judger-example.md"
    if os.path.exists(fallback_file):
        print(f"⚠️  [提示词] 数据库中未找到 multi-modal-llm，回退到文件: {fallback_file}")
        with open(fallback_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    raise Exception("无法找到系统提示词：数据库中无 multi-modal-llm 记录，且本地文件不存在")


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
    *, date: str | dt.date, category: str, prompt_id: str, limit: Optional[int] = None, order_by: str = "arxiv_id.asc",
    time_filter: Optional[str] = None, batch_filter: Optional[List[int]] = None
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
        query = (
            db.from_("papers")
            .select("paper_id, arxiv_id, title, authors, abstract, link, author_affiliation, update_time")
            .eq("update_date", date_str)
            .in_("paper_id", part_ids)
        )
        
        # 应用时间筛选（如果提供）- 保留向后兼容
        if time_filter == "after_18":
            query = query.gte("update_time", "18:00:00").lte("update_time", "23:59:59")
        
        # 应用批次筛选（如果提供）
        if batch_filter:
            query = query.in_("paper_id", batch_filter)
        
        part = query.order("arxiv_id").execute().data
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
            "id": p.get("arxiv_id", ""),  # 添加id字段供前端使用
            "paper_id": p.get("paper_id"),
            "analysis_result": json.dumps(row["analysis_result"], ensure_ascii=False, separators=(",", ":")),
            "title": p.get("title", ""),
            "authors": p.get("authors", ""),
            "abstract": p.get("abstract", ""),
            "link": p.get("link", ""),
            "author_affiliation": p.get("author_affiliation", ""),
            "update_time": p.get("update_time", ""),
        })
        if limit and len(articles) >= limit:
            break
    return articles


def get_ingest_batches(date: str | dt.date, category: str) -> Dict[str, Any]:
    """获取指定日期和分类的ingest批次信息"""
    from datetime import datetime, timedelta
    
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    
    try:
        # 获取该日期该分类的所有论文ingest_at信息
        papers_with_ingest = (
            db.from_("paper_categories")
            .select("papers!inner(paper_id, arxiv_id, ingest_at)")
            .eq("category_id", category_id)
            .eq("papers.update_date", date_str)
            .order("ingest_at", foreign_table="papers")
            .range(0, 9999)
            .execute()
            .data
        )
        
        # 展开papers字段
        papers = []
        for item in papers_with_ingest:
            paper = item.get("papers", {})
            if paper:
                papers.append(paper)
        
        if not papers:
            return {
                'date': date_str,
                'category': category,
                'total_papers': 0,
                'batch_count': 0,
                'batches': []
            }
        
        # 按ingest_at时间进行批次分组
        # 设置批次间隔阈值（30分钟）
        batch_threshold = timedelta(minutes=30)
        
        batches = []
        current_batch = [papers[0]]
        last_time = datetime.fromisoformat(papers[0]['ingest_at'].replace('Z', '+00:00').replace('+00:00', ''))
        
        for paper in papers[1:]:
            current_time = datetime.fromisoformat(paper['ingest_at'].replace('Z', '+00:00').replace('+00:00', ''))
            
            if current_time - last_time > batch_threshold:
                # 开始新批次
                batches.append(current_batch)
                current_batch = [paper]
            else:
                current_batch.append(paper)
            
            last_time = current_time
        
        # 添加最后一个批次
        if current_batch:
            batches.append(current_batch)
        
        # 构造返回数据
        batch_info = []
        for i, batch in enumerate(batches, 1):
            batch_start = datetime.fromisoformat(batch[0]['ingest_at'].replace('Z', '+00:00').replace('+00:00', ''))
            
            batch_info.append({
                'batch_id': i,
                'batch_label': batch_start.strftime('%m-%d %H:%M'),
                'start_time': batch_start.isoformat(),
                'paper_count': len(batch),
                'paper_ids': [p['paper_id'] for p in batch]
            })
        
        return {
            'date': date_str,
            'category': category,
            'total_papers': len(papers),
            'batch_count': len(batches),
            'batches': batch_info
        }
        
    except Exception as e:
        print(f"获取批次信息失败: {e}")
        return {
            'date': date_str,
            'category': category,
            'total_papers': 0,
            'batch_count': 0,
            'batches': []
        }


def get_analysis_status_fast(date: str | dt.date, category: str, prompt_id: str) -> Dict[str, int]:
    """获取指定日期和分类的分析进度状态（高性能优化版本）。"""
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    
    print(f"🚀 [性能优化] 开始获取分析状态: date={date_str}, category={category}")
    start_time = time.time()
    
    try:
        # 🚀 优化策略：使用高效的JOIN查询一次性获取数据
        # 使用内联JOIN获取该日期+分类的所有论文，左连接分析结果
        print(f"⏱️  [性能优化] 开始JOIN查询...")
        
        joined_rows = (
            db.from_("paper_categories")
            .select("papers!inner(paper_id), analysis_results!left(analysis_id)")
            .eq("category_id", category_id)
            .eq("papers.update_date", date_str)
            .eq("analysis_results.prompt_id", prompt_id)
            .range(0, 9999)  # 支持最多10000篇论文
            .execute()
            .data
        )
        
        print(f"⏱️  [性能优化] JOIN查询完成，返回: {len(joined_rows)} 条")
        
        # 统计结果
        total = len(joined_rows)
        completed = 0
        
        for row in joined_rows:
            # 检查是否有分析结果
            analysis_results = row.get("analysis_results")
            if analysis_results and len(analysis_results) > 0:
                completed += 1
        
        pending = max(total - completed, 0)
        result = {"total": total, "completed": completed, "pending": pending}
        
        total_elapsed = time.time() - start_time
        print(f"✅ [性能优化] JOIN查询完成，总耗时: {total_elapsed:.3f}s | 结果: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ [性能优化] JOIN查询失败，回退到传统方法: {e}")
        return get_analysis_status_legacy(date, category, prompt_id)


def get_analysis_status_legacy(date: str | dt.date, category: str, prompt_id: str) -> Dict[str, int]:
    """原始的分块查询版本（用作最终回退）。"""
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    
    print(f"🔄 [回退模式] 使用原始分块查询")
    start_time = time.time()
    
    # 所有该分类下的 paper_id（优化：增大页面大小）
    all_category_paper_ids: List[int] = []
    page_size = 2000  # 增大页面大小
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
    
    # 该日期的论文（优化：增大chunk_size）
    date_paper_ids = []
    chunk_size = 200  # 增大chunk_size
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
    
    # 已分析的论文
    completed_paper_ids = []
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
    
    result = {"total": total, "completed": completed, "pending": pending}
    total_elapsed = time.time() - start_time
    print(f"🔄 [回退模式] 分块查询完成，总耗时: {total_elapsed:.3f}s | 结果: {result}")
    
    return result


def get_analysis_status_original(date: str | dt.date, category: str, prompt_id: str) -> Dict[str, int]:
    """原始未优化版本，用于对比验证。"""
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    
    print(f"🔍 [原始版本] 开始获取分析状态: date={date_str}, category={category}")
    start_time = time.time()
    
    # 所有该分类下的 paper_id
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
    
    print(f"🔍 [原始版本] 分类下总paper_id数: {len(all_category_paper_ids)}")
    
    if not all_category_paper_ids:
        return {"total": 0, "completed": 0, "pending": 0}
    
    # 该日期 + 该分类的 paper_id 集合
    date_paper_ids = []
    chunk_size = 100  # 轻微优化：从50增加到100
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
    print(f"🔍 [原始版本] 该日期下paper_id数: {total}")
    
    if total == 0:
        return {"total": 0, "completed": 0, "pending": 0}
    
    # 已完成（仅统计该日期集合）
    completed_paper_ids = []
    # 使用稍大的chunk_size用于分析结果查询
    analysis_chunk_size = 150  # 对分析结果查询使用更大的chunk
    for i in range(0, len(date_paper_ids), analysis_chunk_size):
        chunk_ids = date_paper_ids[i:i + analysis_chunk_size]
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
    
    result = {"total": total, "completed": completed, "pending": pending}
    total_elapsed = time.time() - start_time
    print(f"🔍 [原始版本] 分析状态获取完成，总耗时: {total_elapsed:.3f}s | 结果: {result}")
    
    return result


def get_analysis_status_optimized(date: str | dt.date, category: str, prompt_id: str) -> Dict[str, int]:
    """优化版本：保持原逻辑但提升性能。"""
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    
    print(f"🚀 [优化版本] 开始获取分析状态: date={date_str}, category={category}")
    start_time = time.time()
    
    # 所有该分类下的 paper_id（优化：增大页面大小）
    all_category_paper_ids: List[int] = []
    page_size = 2000  # 从1000增加到2000
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
    
    print(f"🚀 [优化版本] 分类下总paper_id数: {len(all_category_paper_ids)}")
    
    if not all_category_paper_ids:
        return {"total": 0, "completed": 0, "pending": 0}
    
    # 该日期 + 该分类的 paper_id 集合（优化：增大chunk_size）
    date_paper_ids = []
    chunk_size = 200  # 从50增加到200
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
    print(f"🚀 [优化版本] 该日期下paper_id数: {total}")
    
    if total == 0:
        return {"total": 0, "completed": 0, "pending": 0}
    
    # 已完成（仅统计该日期集合）（优化：使用相同的大chunk_size）
    completed_paper_ids = []
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
    
    result = {"total": total, "completed": completed, "pending": pending}
    total_elapsed = time.time() - start_time
    print(f"✅ [优化版本] 分析状态获取完成，总耗时: {total_elapsed:.3f}s | 结果: {result}")
    
    return result


def get_analysis_status(date: str | dt.date, category: str, prompt_id: str) -> Dict[str, int]:
    """获取指定日期和分类的分析进度状态（入口函数）。"""
    # 回退到原始版本，确保功能正确性优先
    return get_analysis_status_original(date, category, prompt_id)


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




