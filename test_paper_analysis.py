#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os
import json
from doubao_client import DoubaoClient

def read_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return None

def analyze_paper(client, system_prompt, title, abstract):
    """分析单篇论文"""
    try:
        # 构建user prompt
        user_prompt = f"Title: {title}\nAbstract: {abstract}"
        
        response = client.chat(
            message=user_prompt,
            system_prompt=system_prompt,
            verbose=False  # 简化输出
        )
        
        if response:
            try:
                # 尝试解析JSON
                parsed_json = json.loads(response)
                return parsed_json
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                print(f"原始回复: {response}")
                return None
        else:
            print("模型调用失败")
            return None
            
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        return None

def parse_markdown_table(file_path):
    """解析markdown表格"""
    try:
        # 读取markdown文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分割行
        lines = content.strip().split('\n')
        
        # 找到表格数据行（跳过表头和分隔符）
        data_lines = []
        for i, line in enumerate(lines):
            if i >= 2 and line.startswith('|'):  # 跳过表头和分隔符行
                data_lines.append(line)
        
        # 解析数据
        papers = []
        for line in data_lines:
            # 分割表格列
            columns = [col.strip() for col in line.split('|')[1:-1]]  # 去掉首尾的空列
            
            if len(columns) >= 6:  # 确保有足够的列
                paper = {
                    'no': columns[0].strip(),
                    'number_id': columns[1].strip(), 
                    'title': columns[2].strip(),
                    'authors': columns[3].strip(),
                    'abstract': columns[4].strip(),
                    'link': columns[5].strip()
                }
                papers.append(paper)
        
        return papers
        
    except Exception as e:
        print(f"解析markdown表格失败: {e}")
        return []

def test_paper_analysis():
    """测试论文分析功能"""
    
    print("=" * 80)
    print("论文分析测试 - 前10篇论文")
    print("=" * 80)
    
    # 读取system prompt
    system_prompt = read_file_content("prompt/system_prompt.md")
    if not system_prompt:
        print("无法读取system_prompt.md")
        return
    
    # 解析原始markdown文件
    papers = parse_markdown_table("log/2025-07-28-cs.CV-result.md")
    if not papers:
        print("无法解析markdown文件")
        return
    
    print(f"成功解析 {len(papers)} 篇论文")
    print("-" * 50)
    
    # 创建doubao客户端
    client = DoubaoClient()
    
    # 测试前10篇论文
    test_count = min(10, len(papers))
    
    for i in range(test_count):
        paper = papers[i]
        
        print(f"\n【第 {i+1} 篇论文】")
        print(f"标题: {paper['title'][:100]}...")
        print(f"摘要: {paper['abstract'][:200]}...")
        print("-" * 40)
        
        # 调用论文分析
        analysis_result = analyze_paper(client, system_prompt, paper['title'], paper['abstract'])
        
        if analysis_result:
            print("✅ 分析成功:")
            print(f"   通过过滤: {'是' if analysis_result.get('pass_filter') else '否'}")
            
            if analysis_result.get('pass_filter'):
                print(f"   评分: {analysis_result.get('norm_score', 0)}/10")
                print(f"   核心特征分: {sum(analysis_result.get('core_features', {}).values()) * 2}")
                print(f"   加分特征分: {sum(analysis_result.get('plus_features', {}).values())}")
            else:
                print(f"   排除原因: {analysis_result.get('exclude_reason', 'Unknown')}")
            
            print(f"   评价理由: {analysis_result.get('reason', 'No reason provided')}")
            
            # 将分析结果转换为紧凑的JSON字符串用于表格
            compact_json = json.dumps(analysis_result, ensure_ascii=False, separators=(',', ':'))
            print(f"   JSON结果: {compact_json[:150]}...")
        else:
            print("❌ 分析失败")
        
        print("=" * 80)

if __name__ == "__main__":
    test_paper_analysis()