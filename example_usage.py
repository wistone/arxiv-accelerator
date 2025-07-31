#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用示例：展示如何使用crawl_arxiv_cv函数
"""

import importlib.util
from datetime import datetime, timedelta

# 动态导入模块
spec = importlib.util.spec_from_file_location("crawl_raw_info", "crawl-raw-info.py")
crawl_raw_info = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crawl_raw_info)
crawl_arxiv_cv = crawl_raw_info.crawl_arxiv_cv

def main():
    """主函数：演示如何使用crawl_arxiv_cv函数"""
    
    print("=== arXiv CS.CV 论文爬取工具使用示例 ===\n")
    
    # 示例1：爬取今天的论文
    print("1. 爬取今天的论文")
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"   日期: {today}")
    
    success = crawl_arxiv_cv(today)
    if success:
        print(f"   ✓ 成功爬取到论文，结果保存在: log/{today}-result.md")
        print(f"   ✓ 日志保存在: log/{today}-log.txt")
    else:
        print("   ✗ 爬取失败")
    
    print("\n" + "-"*50 + "\n")
    
    # 示例2：爬取指定日期的论文
    print("2. 爬取指定日期的论文")
    target_date = "2025-07-30"
    print(f"   日期: {target_date}")
    
    success2 = crawl_arxiv_cv(target_date)
    if success2:
        print(f"   ✓ 成功爬取到论文，结果保存在: log/{target_date}-result.md")
        print(f"   ✓ 日志保存在: log/{target_date}-log.txt")
    else:
        print("   ✗ 爬取失败")
    
    print("\n" + "-"*50 + "\n")
    
    # 示例3：批量爬取最近几天的论文
    print("3. 批量爬取最近3天的论文")
    for i in range(3):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        print(f"   正在爬取 {date_str} 的论文...")
        
        success = crawl_arxiv_cv(date_str)
        if success:
            print(f"   ✓ {date_str} 爬取成功")
        else:
            print(f"   ✗ {date_str} 爬取失败")
    
    print("\n=== 爬取完成 ===")
    print("所有结果文件都保存在 log/ 文件夹中")
    print("文件命名格式：")
    print("  - 日志文件：YYYY-MM-DD-log.txt")
    print("  - 结果文件：YYYY-MM-DD-result.md")

if __name__ == "__main__":
    main() 