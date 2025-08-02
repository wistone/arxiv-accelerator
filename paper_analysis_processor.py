#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import os
import json
import argparse
from datetime import datetime
from doubao_client import DoubaoClient

def read_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return None

def analyze_paper(client, system_prompt, title, abstract, max_retries=3):
    """分析单篇论文"""
    import time
    
    for attempt in range(max_retries):
        try:
            print(f"开始分析论文 (第{attempt+1}/{max_retries}次尝试): {title[:50]}...")
            
            # 构建user prompt
            user_prompt = f"Title: {title}\nAbstract: {abstract}"
            
            print("正在调用AI模型...")
            start_time = time.time()
            
            response = client.chat(
                message=user_prompt,
                system_prompt=system_prompt,
                verbose=False  # 简化输出
            )
            
            elapsed_time = time.time() - start_time
            print(f"AI模型响应完成，耗时: {elapsed_time:.2f}秒，响应长度: {len(response) if response else 0}")
            
            if response:
                try:
                    # 尝试解析JSON
                    parsed_json = json.loads(response)
                    # 返回紧凑的JSON字符串
                    result = json.dumps(parsed_json, ensure_ascii=False, separators=(',', ':'))
                    print(f"✅ JSON解析成功: {result[:100]}...")
                    return result
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    if attempt < max_retries - 1:
                        print(f"⏭️  将重试...")
                        time.sleep(2 ** attempt)  # 指数退避
                        continue
                    else:
                        error_result = f"{{\"error\": \"JSON parsing failed after {max_retries} attempts: {str(e)}\"}}"
                        print(f"返回错误结果: {error_result}")
                        return error_result
            else:
                print(f"❌ 模型调用失败 (第{attempt+1}次)")
                if attempt < max_retries - 1:
                    print(f"⏭️  将重试...")
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                else:
                    error_result = f"{{\"error\": \"Model call failed after {max_retries} attempts\"}}"
                    print(f"返回错误结果: {error_result}")
                    return error_result
                    
        except Exception as e:
            print(f"❌ 分析过程中出现错误 (第{attempt+1}次): {e}")
            if attempt < max_retries - 1:
                print(f"⏭️  将重试...")
                time.sleep(2 ** attempt)  # 指数退避
                continue
            else:
                error_result = f"{{\"error\": \"Analysis error after {max_retries} attempts: {str(e)}\"}}"
                print(f"异常处理返回: {error_result}")
                return error_result
    
    # 不应该到达这里，但以防万一
    return "{\"error\": \"Unexpected error in analyze_paper\"}"

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

def escape_markdown_content(content):
    """转义markdown表格中的特殊字符"""
    if not content:
        return ""
    
    # 转义管道符号
    content = content.replace('|', '\\|')
    # 转义换行符
    content = content.replace('\n', ' ')
    return content

def generate_analysis_markdown(papers, output_file):
    """生成分析结果的markdown文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入表头
            f.write("|   No. |   analysis_result | title | authors | abstract | link |\n")
            f.write("|------:|:------------------|:------|:--------|:---------|:-----|\n")
            
            # 写入数据行
            for paper in papers:
                no = escape_markdown_content(paper['no'])
                analysis_result = escape_markdown_content(paper.get('analysis_result', ''))
                title = escape_markdown_content(paper['title'])
                authors = escape_markdown_content(paper['authors'])
                abstract = escape_markdown_content(paper['abstract'])
                link = escape_markdown_content(paper['link'])
                
                f.write(f"|{no:>6} | {analysis_result} | {title} | {authors} | {abstract} | {link} |\n")
        
        print(f"✅ 分析结果已保存到: {output_file}")
        
    except Exception as e:
        print(f"生成markdown文件失败: {e}")

def generate_analysis_fail_markdown(papers, output_file, error_count):
    """生成分析失败的markdown文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入失败状态说明
            f.write("# 📋 论文分析失败报告\n\n")
            f.write(f"**状态**: ❌ 分析失败\n\n")
            f.write(f"**总计论文数**: {len(papers)}\n\n")
            f.write(f"**失败数**: {error_count}\n\n")
            f.write(f"**失败时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("**失败原因**: 所有论文的AI分析都失败了，可能的原因包括：\n")
            f.write("- API调用失败\n")
            f.write("- 网络连接问题\n")
            f.write("- AI模型服务异常\n")
            f.write("- 配置错误\n\n")
            f.write("---\n\n")
            f.write("## 📄 尝试分析的论文列表\n\n")
            
            # 写入表头
            f.write("|   No. |   错误信息 | title | authors | abstract | link |\n")
            f.write("|------:|:----------|:------|:--------|:---------|:-----|\n")
            
            # 写入数据行
            for paper in papers:
                no = escape_markdown_content(paper['no'])
                # 尝试从analysis_result中提取错误信息
                analysis_result = paper.get('analysis_result', '')
                if '"error"' in analysis_result:
                    error_msg = "API调用失败"
                else:
                    error_msg = "未知错误"
                    
                title = escape_markdown_content(paper['title'])
                authors = escape_markdown_content(paper['authors'])
                abstract = escape_markdown_content(paper['abstract'])
                link = escape_markdown_content(paper['link'])
                
                f.write(f"|{no:>6} | {error_msg} | {title} | {authors} | {abstract} | {link} |\n")
        
        print(f"❌ 分析失败结果已保存到: {output_file}")
        
    except Exception as e:
        print(f"生成失败markdown文件失败: {e}")

def process_paper_file(input_file, test_count=None):
    """处理论文文件"""
    
    print("=" * 80)
    print(f"处理论文文件: {input_file}")
    print("=" * 80)
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"❌ 输入文件不存在: {input_file}")
        return
    
    # 读取system prompt
    system_prompt = read_file_content("prompt/system_prompt.md")
    if not system_prompt:
        print("❌ 无法读取system_prompt.md")
        return
    
    # 解析原始markdown文件
    papers = parse_markdown_table(input_file)
    if not papers:
        print("❌ 无法解析markdown文件")
        return
    
    print(f"成功解析 {len(papers)} 篇论文")
    
    # 如果指定了测试数量，只处理前N篇
    if test_count:
        papers = papers[:test_count]
        print(f"测试模式：只处理前 {len(papers)} 篇论文")
    
    print("-" * 50)
    
    # 创建doubao客户端
    client = DoubaoClient()
    
    # 处理每篇论文
    for i, paper in enumerate(papers):
        print(f"正在处理第 {i+1}/{len(papers)} 篇论文: {paper['title'][:50]}...")
        
        # 调用论文分析
        analysis_result = analyze_paper(client, system_prompt, paper['title'], paper['abstract'])
        paper['analysis_result'] = analysis_result
        
        # 简单的进度显示
        if (i + 1) % 5 == 0:
            print(f"已完成 {i+1}/{len(papers)} 篇论文")
    
    # 生成输出文件名
    base_name = os.path.basename(input_file)
    if base_name.endswith('-result.md'):
        output_name = base_name.replace('-result.md', '-analysis.md')
    else:
        output_name = base_name.replace('.md', '-analysis.md')
    
    output_file = os.path.join('log', output_name)
    
    # 生成分析结果文件
    generate_analysis_markdown(papers, output_file)
    
    print("=" * 80)
    print("处理完成！")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print(f"处理论文数: {len(papers)}")
    print("=" * 80)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='处理论文markdown文件并生成分析结果')
    parser.add_argument('input_file', help='输入的markdown文件路径')
    parser.add_argument('--test', type=int, help='测试模式：只处理前N篇论文')
    
    args = parser.parse_args()
    
    process_paper_file(args.input_file, args.test)

if __name__ == "__main__":
    # 如果没有提供命令行参数，使用默认测试
    import sys
    if len(sys.argv) == 1:
        print("使用默认测试模式：处理前10篇论文")
        process_paper_file("log/2025-07-28-cs.CV-result.md", test_count=10)
    else:
        main()