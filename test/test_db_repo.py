#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import date

from db.repo import (
    get_or_create_prompt,
    upsert_category,
    upsert_paper,
    link_paper_category,
    list_papers_by_date_category,
    get_prompt_id_by_name,
    list_unanalyzed_papers,
    insert_analysis_result,
    get_analysis_results,
    get_analysis_status,
)


def main():
    # basic env check
    for k in ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"]:
        print(f"{k} set?", bool(os.getenv(k)))

    # seed prompt
    prompt_id = get_or_create_prompt("system_default")
    print("prompt_id:", prompt_id)

    # seed category
    upsert_category("cs.CV")

    # create paper
    pid = upsert_paper(
        arxiv_id="test-0001v1",
        title="Test Title",
        authors="Foo, Bar",
        abstract="Hello world",
        link="https://arxiv.org/abs/test-0001v1",
        update_date=date.today(),
        primary_category="cs.CV",
    )
    link_paper_category(pid, "cs.CV")

    # list papers
    papers = list_papers_by_date_category(date.today(), "cs.CV")
    print("papers:", len(papers))

    # pending
    pending = list_unanalyzed_papers(date.today(), "cs.CV", prompt_id, limit=10)
    print("pending:", len(pending))

    if pending:
        # insert one analysis
        analysis_json = {
            "pass_filter": True,
            "raw_score": 7,
            "norm_score": 7,
            "reason": "ok",
            "core_features": {"multi_modal": 1, "large_scale": 1, "unified_framework": 0, "novel_paradigm": 0},
            "plus_features": {"new_benchmark": 0, "sota": 1, "fusion_arch": 0, "real_world_app": 0, "reasoning_planning": 0, "scaling_modalities": 0, "open_source": 0},
        }
        insert_analysis_result(paper_id=pid, prompt_id=prompt_id, analysis_json=analysis_json, created_by=None)

    # results
    res = get_analysis_results(date=date.today(), category="cs.CV", prompt_id=prompt_id, limit=10)
    print("analysis results:", len(res))

    # status
    st = get_analysis_status(date.today(), category="cs.CV", prompt_id=prompt_id)
    print("status:", st)


if __name__ == "__main__":
    main()


