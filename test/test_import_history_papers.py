#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量导入历史 papers：从 2025-07-22 到今天的 cs.CV / cs.LG / cs.AI。

用法：
  PYTHONPATH="/Users/shijianping/FunnyStaff/arxiv-accelerator:$PYTHONPATH" \
  python3 test/test_import_history_papers.py

说明：
  - 会调用 import_arxiv_to_db.import_arxiv_papers_to_db，自动跳过已存在 arxiv_id。
  - 每天每类打印导入统计，便于观察。
"""

import datetime as dt
import os
from typing import List

from import_arxiv_to_db import import_arxiv_papers_to_db


def daterange(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur = cur + dt.timedelta(days=1)


def main():
    # Mode 1: 2025-07-29 ~ 2025-08-07 Only full analysis
    start_date = [dt.date(2025, 7, 29), dt.date(2025, 7, 30),  dt.date(2025, 7, 30),
         dt.date(2025, 7, 31), dt.date(2025, 7, 31),  dt.date(2025, 7, 31),
         dt.date(2025, 8, 1), dt.date(2025, 8, 2),  dt.date(2025, 8, 2),
         dt.date(2025, 8, 3), dt.date(2025, 8, 4),  dt.date(2025, 8, 5),
         dt.date(2025, 8, 6), dt.date(2025, 8, 7)] 
    cat = ["cs.CV", "cs.CV", "cs.LG", "cs.AI", "cs.CV", "cs.LG", 
         "cs.CV", "cs.AI", "cs.CV", "cs.CV", "cs.CV", "cs.CV", "cs.CV", "cs.CV"]

    for i in range(len(start_date)):
        stats = import_arxiv_papers_to_db(start_date[i].isoformat(), cat[i], limit=None, skip_if_exists=True)
        print(f"结果: {stats}")

    ## Mode 2: From start_date to today
    # start_date = dt.date(2025, 7, 29)
    # today = dt.date.today()
    # categories: List[str] = ["cs.CV", "cs.LG", "cs.AI"]

    # print(f"开始批量导入：{start_date} ~ {today} | 分类: {', '.join(categories)}")

    # total_days = 0
    # for d in daterange(start_date, today):
    #     date_str = d.isoformat()
    #     print("\n" + "=" * 80)
    #     print(f"日期 {date_str}")
    #     print("=" * 80)
    #     for cat in categories:
    #         print(f"-- 类别 {cat}")
    #         stats = import_arxiv_papers_to_db(date_str, cat, limit=None, skip_if_exists=True)
    #         print(f"结果: {stats}")
    #     total_days += 1

    # print(f"\n完成。处理天数: {total_days}")


if __name__ == "__main__":
    main()


