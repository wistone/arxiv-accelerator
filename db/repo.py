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


def list_papers_by_date_category(date: str | dt.date, category: str) -> List[Dict[str, Any]]:
    db = app_schema()
    date_str = _ensure_date(date)
    # join papers with categories via link (two-phase query because postgrest client lacks join)
    # Since supabase-py does not provide join, use SQL via postgrest rpc: emulate with filter + in
    # First, find paper_ids in this category
    paper_ids = (
        db.from_("paper_categories")
        .select("paper_id")
        .in_("category_id", [upsert_category(category)])
        .execute()
        .data
    )
    ids = [row["paper_id"] for row in paper_ids]
    if not ids:
        return []
    rows = (
        db.from_("papers")
        .select("paper_id, arxiv_id, title, authors, abstract, link, author_affiliation")
        .in_("paper_id", ids)
        .eq("update_date", date_str)
        .order("arxiv_id")
        .execute()
        .data
    )
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
    # paper ids by category
    category_id = upsert_category(category)
    paper_ids_rows = db.from_("paper_categories").select("paper_id").eq("category_id", category_id).execute().data
    paper_ids = [r["paper_id"] for r in paper_ids_rows]
    if not paper_ids:
        return []

    # already analyzed for this prompt
    analyzed_rows = (
        db.from_("analysis_results").select("paper_id").eq("prompt_id", prompt_id).in_("paper_id", paper_ids).execute().data
    )
    analyzed_ids = {r["paper_id"] for r in analyzed_rows}

    # candidate papers (by date)
    candidates = (
        db.from_("papers")
        .select("paper_id, arxiv_id, title, authors, abstract, link, author_affiliation")
        .eq("update_date", date_str)
        .in_("paper_id", paper_ids)
        .execute()
        .data
    )

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
    *, date: str | dt.date, category: str, prompt_id: str, limit: Optional[int] = None, order_by: str = "norm_score.desc"
) -> List[Dict[str, Any]]:
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    # paper ids of category
    paper_ids_rows = db.from_("paper_categories").select("paper_id").eq("category_id", category_id).execute().data
    paper_ids = [r["paper_id"] for r in paper_ids_rows]
    if not paper_ids:
        return []

    # analysis rows
    q = (
        db.from_("analysis_results")
        .select("paper_id, analysis_result, norm_score")
        .eq("prompt_id", prompt_id)
        .in_("paper_id", paper_ids)
        .order("norm_score", desc=True)
    )
    if limit:
        q = q.limit(limit)
    analysis_rows = q.execute().data
    analyzed_ids = {r["paper_id"] for r in analysis_rows}

    if not analyzed_ids:
        return []

    # papers details
    papers_rows = (
        db.from_("papers")
        .select("paper_id, arxiv_id, title, authors, abstract, link, author_affiliation")
        .eq("update_date", date_str)
        .in_("paper_id", list(analyzed_ids))
        .execute()
        .data
    )
    meta_by_id = {r["paper_id"]: r for r in papers_rows}

    # build legacy articles output (with analysis_result serialized to string)
    articles: List[Dict[str, Any]] = []
    for idx, row in enumerate(analysis_rows, start=1):
        m = meta_by_id.get(row["paper_id"]) or {}
        articles.append({
            "number": idx,
            "analysis_result": json.dumps(row["analysis_result"], ensure_ascii=False, separators=(",", ":")),
            "title": m.get("title", ""),
            "authors": m.get("authors", ""),
            "abstract": m.get("abstract", ""),
            "link": m.get("link", ""),
            "author_affiliation": m.get("author_affiliation", ""),
        })
    return articles


def get_analysis_status(date: str | dt.date, category: str, prompt_id: str) -> Dict[str, int]:
    db = app_schema()
    date_str = _ensure_date(date)
    category_id = upsert_category(category)
    paper_ids_rows = db.from_("paper_categories").select("paper_id").eq("category_id", category_id).execute().data
    paper_ids = [r["paper_id"] for r in paper_ids_rows]
    if not paper_ids:
        return {"total": 0, "completed": 0, "pending": 0}
    total_rows = db.from_("papers").select("paper_id", count="exact").eq("update_date", date_str).in_("paper_id", paper_ids).execute()
    total = total_rows.count or 0
    completed_rows = db.from_("analysis_results").select("paper_id", count="exact").eq("prompt_id", prompt_id).in_("paper_id", paper_ids).execute()
    completed = completed_rows.count or 0
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


