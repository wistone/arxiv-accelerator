#!/usr/bin/env python3
"""
GROBID批量测试脚本

测试 parse_author_org_v3.py 脚本的稳定性和准确性
读取 log/2025-07-31-cs.CV-result.md 文件中的所有论文链接
输出每个论文的标题和作者机构信息
"""

import sys
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple

# 添加父目录到路径，以便导入主脚本
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parse_author_org_v3
import grobid_tei_xml

def extract_paper_links_from_file(file_path: str) -> List[str]:
    """
    从markdown文件中提取所有ArXiv论文链接
    """
    links = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 使用正则表达式提取所有ArXiv链接
            pattern = r'http://arxiv\.org/abs/[^\s|)]+|https://arxiv\.org/abs/[^\s|)]+'
            found_links = re.findall(pattern, content)
            # 去重并清理链接
            for link in found_links:
                clean_link = link.strip('|).;:')
                if clean_link not in links:
                    links.append(clean_link)
    except Exception as e:
        print(f"读取文件时出错: {e}")
    
    return links

def get_paper_title_from_grobid(xml_content: str) -> str:
    """
    从GROBID XML中提取论文标题
    """
    try:
        doc = grobid_tei_xml.parse_document_xml(xml_content)
        return doc.header.title if doc.header.title else "标题提取失败"
    except:
        return "标题解析错误"

def process_paper_with_title(arxiv_url: str) -> Tuple[str, List[str]]:
    """
    处理单篇论文，返回标题和机构列表
    """
    try:
        # 下载PDF
        pdf_content = parse_author_org_v3.download_arxiv_pdf(arxiv_url)
        
        # 使用GROBID处理
        xml_content = parse_author_org_v3.process_pdf_with_grobid(pdf_content)
        
        # 提取标题
        title = get_paper_title_from_grobid(xml_content)
        
        # 提取机构
        affiliations = parse_author_org_v3.parse_grobid_xml(xml_content)
        
        return title, affiliations
        
    except Exception as e:
        return f"错误: {str(e)}", []

def run_batch_test(file_path: str, max_papers: int = None):
    """
    运行批量测试
    """
    print("=" * 80)
    print("🧪 GROBID批量测试开始")
    print("=" * 80)
    
    # 提取链接
    links = extract_paper_links_from_file(file_path)
    if not links:
        print("❌ 未找到任何ArXiv链接")
        return
    
    print(f"📄 从文件中提取到 {len(links)} 个论文链接")
    
    if max_papers:
        links = links[:max_papers]
        print(f"🔢 限制测试前 {max_papers} 篇论文")
    
    # 统计信息
    stats = {
        'total': len(links),
        'success': 0,
        'failed': 0,
        'total_affiliations': 0
    }
    
    print(f"\n🚀 开始批量处理 {len(links)} 篇论文...")
    print("=" * 80)
    
    for i, link in enumerate(links, 1):
        print(f"\n[{i}/{len(links)}] 处理论文: {link}")
        arxiv_id = parse_author_org_v3.extract_arxiv_id_from_url(link)
        
        try:
            title, affiliations = process_paper_with_title(link)
            
            if title.startswith("错误:"):
                stats['failed'] += 1
                print(f"❌ 失败 - {title}")
            else:
                stats['success'] += 1
                stats['total_affiliations'] += len(affiliations)
                
                print(f"✅ 成功")
                print(f"📝 标题: {title}")
                print(f"🏢 机构数量: {len(affiliations)}")
                
                if affiliations:
                    print("🏢 作者机构:")
                    for j, affil in enumerate(affiliations, 1):
                        print(f"    {j}. {affil}")
                else:
                    print("🏢 未找到机构信息")
                    
        except Exception as e:
            stats['failed'] += 1
            print(f"❌ 处理异常: {str(e)}")
        
        # 添加延迟以避免服务器过载
        if i < len(links):
            time.sleep(1)
    
    # 打印统计信息
    print("\n" + "=" * 80)
    print("📊 批量测试结果统计")
    print("=" * 80)
    print(f"📄 总论文数: {stats['total']}")
    print(f"✅ 成功处理: {stats['success']}")
    print(f"❌ 处理失败: {stats['failed']}")
    print(f"🏢 总机构数: {stats['total_affiliations']}")
    
    if stats['total'] > 0:
        success_rate = (stats['success'] / stats['total']) * 100
        print(f"📈 成功率: {success_rate:.2f}%")
        
        if stats['success'] > 0:
            avg_affiliations = stats['total_affiliations'] / stats['success']
            print(f"📊 平均每篇论文机构数: {avg_affiliations:.2f}")
    
    print("=" * 80)

if __name__ == "__main__":
    # 默认测试文件路径
    default_file = "../log/2025-07-31-cs.CV-result.md"
    
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit():
            # 如果第一个参数是数字，则为最大论文数
            max_papers = int(sys.argv[1])
            file_path = default_file
        else:
            # 否则为文件路径
            file_path = sys.argv[1]
            max_papers = int(sys.argv[2]) if len(sys.argv) > 2 else None
    else:
        file_path = default_file
        max_papers = None
    
    print(f"📁 测试文件: {file_path}")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    
    # 运行批量测试
    run_batch_test(file_path, max_papers)