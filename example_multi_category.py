#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多分类使用示例：展示如何使用crawl_arxiv_papers函数爬取不同分类的论文
"""

import importlib.util
from datetime import datetime, timedelta

# 动态导入模块
spec = importlib.util.spec_from_file_location("crawl_raw_info", "crawl-raw-info.py")
crawl_raw_info = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crawl_raw_info)
crawl_arxiv_papers = crawl_raw_info.crawl_arxiv_papers

def main():
    """主函数：演示如何使用crawl_arxiv_papers函数爬取不同分类的论文"""
    
    print("=== arXiv 多分类论文爬取工具使用示例 ===\n")
    
    # 示例1：爬取今天的计算机视觉论文
    print("1. 爬取今天的计算机视觉论文")
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"   日期: {today}")
    print(f"   分类: cs.CV")
    
    success = crawl_arxiv_papers(today, "cs.CV")
    if success:
        print(f"   ✓ 成功爬取到论文，结果保存在: log/{today}-cs.CV-result.md")
        print(f"   ✓ 日志保存在: log/{today}-cs.CV-log.txt")
    else:
        print("   ✗ 爬取失败")
    
    print("\n" + "-"*50 + "\n")
    
    # 示例2：爬取今天的机器学习论文
    print("2. 爬取今天的机器学习论文")
    print(f"   日期: {today}")
    print(f"   分类: cs.LG")
    
    success2 = crawl_arxiv_papers(today, "cs.LG")
    if success2:
        print(f"   ✓ 成功爬取到论文，结果保存在: log/{today}-cs.LG-result.md")
        print(f"   ✓ 日志保存在: log/{today}-cs.LG-log.txt")
    else:
        print("   ✗ 爬取失败")
    
    print("\n" + "-"*50 + "\n")
    
    # 示例3：批量爬取不同分类的历史论文
    print("3. 批量爬取不同分类的历史论文")
    test_cases = [
        ("2025-07-25", "cs.CV", "计算机视觉"),
        ("2025-07-25", "cs.LG", "机器学习"),
        ("2025-07-20", "cs.CV", "计算机视觉"),
        ("2025-07-20", "cs.LG", "机器学习"),
    ]
    
    for date, category, description in test_cases:
        print(f"   正在爬取 {date} 的{description}论文...")
        
        success = crawl_arxiv_papers(date, category)
        if success:
            print(f"   ✓ {date} ({category}) 爬取成功")
        else:
            print(f"   ✗ {date} ({category}) 爬取失败")
    
    print("\n=== 爬取完成 ===")
    print("所有结果文件都保存在 log/ 文件夹中")
    print("文件命名格式：")
    print("  - 日志文件：YYYY-MM-DD-category-log.txt")
    print("  - 结果文件：YYYY-MM-DD-category-result.md")
    print("\n支持的分类：")
    print("  - cs.CV: 计算机视觉 (Computer Vision)")
    print("  - cs.LG: 机器学习 (Machine Learning)")

if __name__ == "__main__":
    main() 