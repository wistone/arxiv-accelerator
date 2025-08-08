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

    for idx, cols in enumerate(rows, start=1):
        if len(cols) < 6:
            continue
        analysis_result_text = cols[1].replace('\\|', '|')
        link = cols[5].replace('\\|', '|')
        author_affil = cols[6].replace('\\|', '|') if has_author_affil and len(cols) >= 7 else None

        try:
            arxiv_id = extract_arxiv_id_from_link(link)
            paper_id = db_repo.get_paper_id_by_arxiv_id(arxiv_id)
            if not paper_id:
                papers_missing += 1
                print(f"[{idx}] 跳过：找不到paper arxiv_id={arxiv_id}")
                continue

            if db_repo.analysis_exists(paper_id, prompt_id):
                skipped += 1
                print(f"[{idx}] 跳过已存在分析：arxiv_id={arxiv_id}")
                continue

            # 确保analysis_result为合法JSON
            try:
                parsed = json.loads(analysis_result_text)
            except Exception as e:
                print(f"[{idx}] 解析analysis_result失败：{e} | 原文={analysis_result_text[:120]}")
                continue

            db_repo.insert_analysis_result(paper_id=paper_id, prompt_id=prompt_id, analysis_json=parsed, created_by=None)
            updated += 1
            print(f"[{idx}] 写入analysis_results：paper_id={paper_id} arxiv_id={arxiv_id}")

            if author_affil is not None and author_affil != "":
                try:
                    db_repo.update_paper_author_affiliation(paper_id, author_affil)
                    author_updates += 1
                    print(f"    + 更新papers.author_affiliation")
                except Exception as e:
                    print(f"    ! 更新author_affiliation失败：{e}")

        except Exception as e:
            print(f"[{idx}] 处理异常：{e}")

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


