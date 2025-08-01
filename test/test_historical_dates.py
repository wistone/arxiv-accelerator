#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试历史日期查询功能
"""

import importlib.util
from datetime import datetime, timedelta

# 动态导入模块
spec = importlib.util.spec_from_file_location("crawl_raw_info", "crawl-raw-info.py")
crawl_raw_info = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crawl_raw_info)
crawl_arxiv_papers = crawl_raw_info.crawl_arxiv_papers

def test_historical_dates():
    """测试历史日期查询功能"""
    
    print("=== 测试历史日期查询功能 ===\n")
    
    # 测试用例：不同的历史日期和分类
    test_cases = [
        # ("2025-07-25", "cs.CV"),  # 6天前，计算机视觉
        ("2025-07-28", "cs.LG"),  # 6天前，机器学习
        # ("2025-07-20", "cs.CV"),  # 11天前，计算机视觉
        # ("2025-07-20", "cs.LG"),  # 11天前，机器学习
        # ("2025-13-01", "cs.CV"),  # 无效的月份
    ]
    
    for date, category in test_cases:
        print(f"正在测试日期: {date}, 分类: {category}")
        success = crawl_arxiv_papers(date, category)
        
        if success:
            print(f"✓ {date} ({category}) 查询成功")
            
            # 检查生成的文件
            import os
            log_file = f"log/{date}-{category}-log.txt"
            result_file = f"log/{date}-{category}-result.md"
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "submittedDate:[" in content:
                        print(f"  ✓ 使用了日期范围查询")
                    else:
                        print(f"  ✓ 使用了标准查询")
                    
                    # 统计获取的论文数量
                    if "获取到" in content:
                        for line in content.split('\n'):
                            if "获取到" in line and "篇论文" in line:
                                print(f"  {line.strip()}")
                                break
            else:
                print(f"  ✗ 日志文件未生成")
                
            if os.path.exists(result_file):
                file_size = os.path.getsize(result_file)
                print(f"  ✓ 结果文件大小: {file_size} bytes")
            else:
                print(f"  ✗ 结果文件未生成")
        else:
            print(f"✗ {date} ({category}) 查询失败")
        
        print()
    
    print("=== 测试完成 ===")
    print("所有结果文件都保存在 log/ 文件夹中")

if __name__ == "__main__":
    test_historical_dates() 