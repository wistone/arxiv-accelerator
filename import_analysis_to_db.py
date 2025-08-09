#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
将 log/*-analysis*.md 解析并导入数据库：
  - 写入 app.analysis_results（prompt 固定为给定ID）
  - 若表格含 author_affiliation 列（7列），同步更新 app.papers.author_affiliation

用法：
  PYTHONPATH="/Users/shijianping/FunnyStaff/arxiv-accelerator:$PYTHONPATH" \
  python3 import_analysis_to_db.py log/2025-07-22-cs.AI-analysis-top5.md \
    --prompt-id d3094bb1-486e-4297-a274-43be3deea1c1
"""

import os
import re
import json
from typing import List, Dict, Any

from db import repo as db_repo


def parse_markdown_table(filepath: str) -> List[List[str]]:
    rows: List[List[str]] = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('|') and not line.startswith('|------'):
                parts = [p.strip() for p in line.strip().split('|')[1:-1]]
                rows.append(parts)
    # 去掉表头
    if rows:
        rows = rows[1:]
    return rows


def extract_arxiv_id_from_link(link: str) -> str:
    # http://arxiv.org/abs/2507.17083v1 → 2507.17083v1
    m = re.search(r"/abs/([0-9]{4}\.[0-9]{5}v\d+)", link)
    if m:
        return m.group(1)
    # 宽松匹配
    m = re.search(r"([0-9]{4}\.[0-9]{5}v\d+)", link)
    if not m:
        raise ValueError(f"无法从link解析arxiv_id: {link}")
    return m.group(1)


def import_analysis_markdown(filepath: str, prompt_id: str) -> Dict[str, Any]:
    rows = parse_markdown_table(filepath)
    updated = 0
    skipped = 0
    papers_missing = 0
    author_updates = 0

    has_author_affil = False
    if rows:
        has_author_affil = len(rows[0]) >= 7

    # 预解析所有行，收集 arxiv_id、analysis_json、author_affil
    parsed_items: List[Dict[str, Any]] = []
    for idx, cols in enumerate(rows, start=1):
        if len(cols) < 6:
            continue
        analysis_result_text = cols[1].replace('\\|', '|')
        link = cols[5].replace('\\|', '|')
        author_affil = cols[6].replace('\\|', '|') if has_author_affil and len(cols) >= 7 else None
        try:
            arxiv_id = extract_arxiv_id_from_link(link)
            try:
                analysis_json = json.loads(analysis_result_text)
            except Exception as e:
                print(f"[{idx}] 解析analysis_result失败：{e} | 原文={analysis_result_text[:120]}")
                continue
            parsed_items.append({
                "idx": idx,
                "arxiv_id": arxiv_id,
                "analysis_json": analysis_json,
                "author_affil": author_affil,
            })
        except Exception as e:
            print(f"[{idx}] 处理异常：{e}")

    if not parsed_items:
        return {
            "updated": 0,
            "skipped": 0,
            "papers_missing": 0,
            "author_updates": 0,
            "rows": len(rows),
            "has_author_affiliation": has_author_affil,
        }

    # 批量查询 paper_id
    arxiv_ids = [it["arxiv_id"] for it in parsed_items]
    papers = db_repo.get_papers_by_arxiv_ids(arxiv_ids)
    arxiv_to_pid = {r["arxiv_id"]: r["paper_id"] for r in papers}

    # 根据是否存在进行拆分
    items_with_pid = []
    for it in parsed_items:
        pid = arxiv_to_pid.get(it["arxiv_id"]) 
        if not pid:
            papers_missing += 1
            print(f"[{it['idx']}] 跳过：找不到paper arxiv_id={it['arxiv_id']}")
            continue
        it["paper_id"] = pid
        items_with_pid.append(it)

    if not items_with_pid:
        return {
            "updated": 0,
            "skipped": 0,
            "papers_missing": papers_missing,
            "author_updates": 0,
            "rows": len(rows),
            "has_author_affiliation": has_author_affil,
        }

    # 批量查询已存在的分析，避免重复
    paper_ids = [it["paper_id"] for it in items_with_pid]
    existing_pids = set(db_repo.list_existing_analyses_for_prompt(paper_ids, prompt_id))

    # 需要写入的行
    bulk_rows: List[Dict[str, Any]] = []
    for it in items_with_pid:
        if it["paper_id"] in existing_pids:
            skipped += 1
            print(f"[{it['idx']}] 跳过已存在分析：arxiv_id={it['arxiv_id']}")
            continue
        bulk_rows.append({
            "paper_id": it["paper_id"],
            "prompt_id": prompt_id,
            "analysis_result": it["analysis_json"],
            "created_by": None,
        })

    if bulk_rows:
        db_repo.insert_analysis_results_bulk(bulk_rows)
        updated += len(bulk_rows)
        # 打印写入行的信息
        for it in items_with_pid:
            if it["paper_id"] not in existing_pids:
                print(f"[{it['idx']}] 写入analysis_results：paper_id={it['paper_id']} arxiv_id={it['arxiv_id']}")

    # 批量更新 author_affiliation（若提供且非空）
    for it in items_with_pid:
        aff = it.get("author_affil")
        if aff:
            try:
                db_repo.update_paper_author_affiliation(it["paper_id"], aff)
                author_updates += 1
                print("    + 更新papers.author_affiliation")
            except Exception as e:
                print(f"    ! 更新author_affiliation失败：{e}")

    return {
        "updated": updated,
        "skipped": skipped,
        "papers_missing": papers_missing,
        "author_updates": author_updates,
        "rows": len(rows),
        "has_author_affiliation": has_author_affil,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import analysis markdown into DB")
    parser.add_argument("md_file", help="path to *-analysis*.md")
    parser.add_argument("--prompt-id", required=True, help="prompt_id to use for all rows")
    args = parser.parse_args()

    stats = import_analysis_markdown(args.md_file, args.prompt_id)
    print("SUMMARY:", stats)


if __name__ == "__main__":
    main()


