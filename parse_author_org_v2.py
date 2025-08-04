import feedparser
import time
import re
import sys

def extract_arxiv_id_from_url(url: str) -> str:
    """
    从arxiv abstract URL中提取arxiv_id
    例如: http://arxiv.org/abs/2507.23785v1 -> 2507.23785v1
    """
    # 清理URL，移除可能的空格
    url = url.strip()
    
    # 使用正则表达式提取arxiv_id
    pattern = r'/abs/([^/\s]+)/?$'
    match = re.search(pattern, url)
    
    if match:
        return match.group(1)
    else:
        raise ValueError(f"无法从URL中提取arxiv_id: {url}")

def arxiv_affil_via_api(url_or_id: str) -> list:
    """
    从arxiv URL或ID获取作者机构信息
    """
    # 如果输入是URL，先提取arxiv_id
    if url_or_id.startswith('http'):
        arxiv_id = extract_arxiv_id_from_url(url_or_id)
    else:
        arxiv_id = url_or_id
    
    # 使用ArXiv API查询
    api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    feed = feedparser.parse(api_url)
    
    # 检查是否有结果
    if not feed.entries:
        return []
    
    # 提取作者和机构信息
    out = []
    entry = feed.entries[0]
    
    # 检查是否有作者信息
    if hasattr(entry, 'authors') and entry.authors:
        for author in entry.authors:
            author_name = author.get('name', 'Unknown Author')
            affiliation = author.get('affiliation', None)
            
            if affiliation:
                out.append((author_name, affiliation))
            else:
                out.append((author_name, 'No affiliation info'))
    
    return out

def extract_paper_links_from_file(file_path: str) -> list:
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

def test_batch_papers(links: list) -> dict:
    """
    批量测试论文链接，返回统计结果
    """
    results = {
        'total': len(links),
        'success_with_affiliation': 0,  # 成功获取作者且有机构信息
        'success_no_affiliation': 0,    # 成功获取作者但无机构信息
        'failed': 0,                    # 完全失败
        'details': []
    }
    
    print(f"开始测试 {len(links)} 篇论文...")
    print("=" * 80)
    
    for i, link in enumerate(links, 1):
        print(f"\n[{i}/{len(links)}] 测试: {link}")
        
        try:
            # 获取ArXiv ID
            arxiv_id = extract_arxiv_id_from_url(link)
            
            # 获取机构信息
            affiliations = arxiv_affil_via_api(link)
            
            if affiliations:
                # 检查是否有真正的机构信息
                has_real_affiliation = any(affil != 'No affiliation info' for _, affil in affiliations)
                
                if has_real_affiliation:
                    results['success_with_affiliation'] += 1
                    print(f"✅ 成功(有机构) - 论文 {arxiv_id}:")
                    for j, (author, affil) in enumerate(affiliations, 1):
                        print(f"  {j}. {author} - {affil}")
                    
                    results['details'].append({
                        'arxiv_id': arxiv_id,
                        'link': link,
                        'status': 'success_with_affiliation',
                        'affiliations': affiliations
                    })
                else:
                    results['success_no_affiliation'] += 1
                    print(f"🔶 成功(无机构) - 论文 {arxiv_id}:")
                    for j, (author, affil) in enumerate(affiliations, 1):
                        print(f"  {j}. {author} - (无机构信息)")
                    
                    results['details'].append({
                        'arxiv_id': arxiv_id,
                        'link': link,
                        'status': 'success_no_affiliation',
                        'affiliations': affiliations
                    })
            else:
                results['failed'] += 1
                print(f"❌ 失败 - 论文 {arxiv_id}: 未找到任何作者信息")
                
                results['details'].append({
                    'arxiv_id': arxiv_id,
                    'link': link,
                    'status': 'no_authors',
                    'affiliations': []
                })
                
        except Exception as e:
            results['failed'] += 1
            print(f"❌ 错误 - {link}: {e}")
            
            results['details'].append({
                'arxiv_id': 'unknown',
                'link': link,
                'status': 'error',
                'error': str(e),
                'affiliations': []
            })
        
        # 添加延迟以避免API限制
        time.sleep(0.5)
    
    return results

def print_summary(results: dict):
    """
    打印测试结果汇总
    """
    print("\n" + "=" * 80)
    print("📊 ArXiv API 机构信息获取测试结果汇总")
    print("=" * 80)
    print(f"总论文数: {results['total']}")
    print(f"✅ 成功获取作者且有机构信息: {results['success_with_affiliation']}")
    print(f"🔶 成功获取作者但无机构信息: {results['success_no_affiliation']}")
    print(f"❌ 完全失败(无作者信息): {results['failed']}")
    
    if results['total'] > 0:
        success_total = results['success_with_affiliation'] + results['success_no_affiliation']
        api_success_rate = (success_total / results['total']) * 100
        affiliation_success_rate = (results['success_with_affiliation'] / results['total']) * 100
        
        print(f"\n📈 成功率统计:")
        print(f"  - API调用成功率(能获取作者): {api_success_rate:.2f}%")
        print(f"  - 机构信息获取成功率: {affiliation_success_rate:.2f}%")
    
    # 按状态分类统计
    status_count = {}
    for detail in results['details']:
        status = detail['status']
        status_count[status] = status_count.get(status, 0) + 1
    
    print(f"\n📋 详细状态统计:")
    status_descriptions = {
        'success_with_affiliation': '成功获取作者和机构信息',
        'success_no_affiliation': '成功获取作者但无机构信息',
        'no_authors': '无法获取作者信息',
        'error': 'API调用错误'
    }
    
    for status, count in status_count.items():
        desc = status_descriptions.get(status, status)
        print(f"  - {desc}: {count}")
    
    print(f"\n💡 结论:")
    if results['success_with_affiliation'] == 0:
        print("  - ArXiv API通常不提供机构信息，但能成功获取作者姓名")
        print("  - 建议使用PDF解析方法来获取机构信息")
    else:
        print(f"  - 有 {results['success_with_affiliation']} 篇论文提供了机构信息")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法:")
        print("1. 测试单个URL: python parse_author_org_v2.py <arxiv_url>")
        print("2. 批量测试文件中的链接: python parse_author_org_v2.py <file_path>")
        print("3. 使用默认测试文件: python parse_author_org_v2.py default")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg == "default":
        # 使用默认测试文件
        file_path = "log/2025-07-31-cs.CV-result.md"
        print(f"使用默认测试文件: {file_path}")
        
        # 提取链接
        links = extract_paper_links_from_file(file_path)
        if not links:
            print("未找到任何ArXiv链接")
            sys.exit(1)
        
        print(f"从文件中提取到 {len(links)} 个论文链接")
        
        # 批量测试
        results = test_batch_papers(links)
        
        # 打印汇总
        print_summary(results)
        
    elif arg.startswith('http'):
        # 测试单个URL
        print(f"测试单个URL: {arg}")
        try:
            affiliations = arxiv_affil_via_api(arg)
            arxiv_id = extract_arxiv_id_from_url(arg)
            
            print(f"\n论文 {arxiv_id} 的作者机构信息:")
            if affiliations:
                for i, (author, affil) in enumerate(affiliations, 1):
                    print(f"  {i}. {author} - {affil}")
            else:
                print("  未找到机构信息")
        except Exception as e:
            print(f"处理URL时出错: {e}")
            
    else:
        # 测试指定文件中的链接
        file_path = arg
        print(f"从文件提取链接并批量测试: {file_path}")
        
        # 提取链接
        links = extract_paper_links_from_file(file_path)
        if not links:
            print("未找到任何ArXiv链接")
            sys.exit(1)
        
        print(f"从文件中提取到 {len(links)} 个论文链接")
        
        # 批量测试
        results = test_batch_papers(links)
        
        # 打印汇总
        print_summary(results)
