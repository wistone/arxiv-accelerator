#!/usr/bin/env python3
"""
豆包API批量测试脚本

使用豆包API解析ArXiv论文作者机构信息的批量测试
测试 parse_author_org_v4.py 脚本的准确性和稳定性

使用方法：
1. 确保环境变量已配置：
   export DOUBAO_API_KEY='your-api-key'
   export DOUBAO_MODEL='your-model-endpoint'

2. 运行测试：
   cd test
   python test_doubao_batch.py 10              # 测试前10篇论文
   python test_doubao_batch.py                 # 测试所有论文
   python test_doubao_batch.py ../path/file.md # 测试指定文件
   python test_doubao_batch.py ../path/file.md 5 # 测试指定文件前5篇

3. 输出结果：
   - 每个论文的作者机构列表
   - 处理成功率统计
   - 错误信息汇总
"""

import sys
import os
import re
import time
from typing import List, Dict

# 添加父目录到路径，以便导入主脚本
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parse_author_org_v4


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


def process_single_paper(arxiv_url: str) -> Dict:
    """
    处理单篇论文
    """
    arxiv_id = parse_author_org_v4.extract_arxiv_id_from_url(arxiv_url)
    
    try:
        affiliations = parse_author_org_v4.get_author_affiliations(arxiv_url)
        return {
            'arxiv_id': arxiv_id,
            'arxiv_url': arxiv_url,
            'status': 'success',
            'affiliations': affiliations,
            'affiliation_count': len(affiliations)
        }
    except Exception as e:
        return {
            'arxiv_id': arxiv_id,
            'arxiv_url': arxiv_url,
            'status': 'error',
            'error': str(e),
            'affiliations': [],
            'affiliation_count': 0
        }


def run_batch_test(file_path: str, max_papers: int = None):
    """
    运行批量测试
    """
    print("=" * 80)
    print("🤖 豆包API批量测试开始")
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
        'total_affiliations': 0,
        'errors': []
    }
    
    print(f"\n🚀 开始批量处理 {len(links)} 篇论文...")
    print("=" * 80)
    
    results = []
    
    for i, link in enumerate(links, 1):
        print(f"\n[{i}/{len(links)}] 处理论文: {link}")
        
        try:
            result = process_single_paper(link)
            results.append(result)
            
            if result['status'] == 'success':
                stats['success'] += 1
                stats['total_affiliations'] += result['affiliation_count']
                
                print(f"✅ 成功")
                print(f"🏢 机构数量: {result['affiliation_count']}")
                
                if result['affiliations']:
                    print("🏢 作者机构:")
                    for j, affil in enumerate(result['affiliations'], 1):
                        print(f"    {j}. {affil}")
                else:
                    print("🏢 未找到机构信息")
                    
            else:
                stats['failed'] += 1
                stats['errors'].append(f"[{result['arxiv_id']}] {result['error']}")
                print(f"❌ 失败: {result['error']}")
                
        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append(f"[{link}] 处理异常: {str(e)}")
            print(f"❌ 处理异常: {str(e)}")
        
        # 添加延迟以避免API限制
        if i < len(links):
            time.sleep(2)  # 2秒延迟，避免API调用过快
    
    # 打印详细统计信息
    print("\n" + "=" * 80)
    print("📊 豆包API批量测试结果统计")
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
    
    # 打印错误汇总
    if stats['errors']:
        print(f"\n❌ 错误汇总 ({len(stats['errors'])}个):")
        for error in stats['errors']:
            print(f"  - {error}")
    
    print("=" * 80)
    
    return results


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
    
    # 检查环境变量
    try:
        from doubao_client import DoubaoClient
        client = DoubaoClient()
        print("✅ 豆包API配置检查通过")
    except Exception as e:
        print(f"❌ 豆包API配置错误: {e}")
        print("\n请确保已正确设置环境变量:")
        print("  export DOUBAO_API_KEY='your-api-key'")
        print("  export DOUBAO_MODEL='your-model-endpoint'")
        sys.exit(1)
    
    # 运行批量测试
    run_batch_test(file_path, max_papers)