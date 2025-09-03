"""
智能搜索服务模块
基于arXiv ID文本解析和批量获取论文信息
"""

import re
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Tuple
import xml.etree.ElementTree as ET
from datetime import datetime
from ..db import repo as db_repo

def extract_arxiv_ids(text: str) -> List[str]:
    """
    从文本中提取所有arXiv ID
    支持格式: arXiv:2508.21824 或 arXiv:2508.21824v1
    
    Args:
        text: 包含arXiv ID的文本
        
    Returns:
        去重后的arXiv ID列表
    """
    # 匹配 arXiv:xxxx.xxxxx 格式 (可能带版本号如v1, v2等)
    pattern = r'arXiv:(\d{4}\.\d{4,5}(?:v\d+)?)'
    matches = re.findall(pattern, text)
    
    # 去重并保持顺序
    seen = set()
    unique_ids = []
    for match in matches:
        # 去掉版本号，只保留基础ID
        base_id = match.split('v')[0]
        if base_id not in seen:
            seen.add(base_id)
            unique_ids.append(base_id)
    
    return unique_ids

def parse_arxiv_xml(xml_content: str) -> Dict[str, Any]:
    """
    解析arXiv API返回的XML，提取论文信息
    
    Args:
        xml_content: arXiv API返回的XML内容
        
    Returns:
        包含论文信息的字典
    """
    try:
        root = ET.fromstring(xml_content)
        
        # 定义命名空间
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        # 查找entry元素
        entry = root.find('atom:entry', namespaces)
        if entry is None:
            return None
            
        # 提取基本信息
        paper_info = {}
        
        # 标题
        title_elem = entry.find('atom:title', namespaces)
        if title_elem is not None:
            paper_info['title'] = title_elem.text.strip().replace('\n', ' ')
        
        # arXiv ID
        id_elem = entry.find('atom:id', namespaces)
        if id_elem is not None:
            arxiv_url = id_elem.text
            clean_id = arxiv_url.split('/')[-1].replace('v1', '').replace('v2', '').replace('v3', '')
            paper_info['arxiv_id'] = clean_id
            paper_info['id'] = clean_id  # 兼容前端字段名
            paper_info['paper_id'] = None  # 智能搜索的文章没有数据库ID
        
        # 摘要 - 修改字段名为abstract以匹配数据库结构
        summary_elem = entry.find('atom:summary', namespaces)
        if summary_elem is not None:
            paper_info['abstract'] = summary_elem.text.strip().replace('\n', ' ')
        
        # 作者 - 转换为字符串格式，匹配数据库结构
        authors = []
        for author in entry.findall('atom:author', namespaces):
            name_elem = author.find('atom:name', namespaces)
            if name_elem is not None:
                authors.append(name_elem.text)
        paper_info['authors'] = ', '.join(authors) if authors else ''
        
        # 发布日期
        published_elem = entry.find('atom:published', namespaces)
        if published_elem is not None:
            paper_info['published'] = published_elem.text
        
        # 更新日期 - 解析为update_date字段
        updated_elem = entry.find('atom:updated', namespaces)
        if updated_elem is not None:
            paper_info['updated'] = updated_elem.text
            # 解析日期并格式化为YYYY-MM-DD格式
            try:
                # arXiv时间格式：2025-08-25T17:41:27Z
                dt = datetime.fromisoformat(updated_elem.text.replace('Z', '+00:00'))
                paper_info['update_date'] = dt.strftime('%Y-%m-%d')
                print(f"📅 [日期解析] {paper_info.get('arxiv_id', 'N/A')}: {updated_elem.text} -> {paper_info['update_date']}")
            except Exception as e:
                print(f"⚠️  [日期解析] 失败 {updated_elem.text}: {e}")
                paper_info['update_date'] = datetime.now().strftime('%Y-%m-%d')
        else:
            # 没有更新日期时使用今天
            paper_info['update_date'] = datetime.now().strftime('%Y-%m-%d')
        
        # 分类
        categories = []
        for category in entry.findall('atom:category', namespaces):
            term = category.get('term')
            if term:
                categories.append(term)
        paper_info['categories'] = categories
        
        # PDF链接 - 添加link字段以匹配数据库结构
        for link in entry.findall('atom:link', namespaces):
            if link.get('title') == 'pdf':
                paper_info['pdf_url'] = link.get('href')
                paper_info['link'] = link.get('href')  # 匹配数据库结构
                break
        
        # 如果没有找到PDF链接，使用arXiv主页链接
        if 'link' not in paper_info and 'arxiv_id' in paper_info:
            paper_info['link'] = f"https://arxiv.org/abs/{paper_info['arxiv_id']}"
        
        # 机构信息 - 智能搜索暂时不包含
        paper_info['author_affiliation'] = ''
        
        return paper_info
        
    except Exception as e:
        print(f"解析XML失败: {e}")
        return None

def fetch_arxiv_papers_batch(arxiv_ids: List[str], timeout: int = 30) -> Dict[str, Any]:
    """
    通过arXiv API批量获取多篇论文详细信息
    
    Args:
        arxiv_ids: arXiv论文ID列表
        timeout: 请求超时时间（秒）
        
    Returns:
        包含状态和内容的字典
    """
    if not arxiv_ids:
        return {
            'status': 'error',
            'message': '没有提供arXiv ID',
            'found_papers': [],
            'not_exist_ids': [],
            'error_ids': []
        }
    
    # 构建批量API URL
    base_url = "http://export.arxiv.org/api/query?"
    # 使用id_list参数进行批量查询
    id_list = ','.join(arxiv_ids)
    params = {
        'id_list': id_list,
        'start': 0,
        'max_results': min(len(arxiv_ids), 500)  # 扩展到500篇论文
    }
    
    url = base_url + urllib.parse.urlencode(params)
    print(f"🚀 [批量查询] 开始批量获取 {len(arxiv_ids)} 篇论文信息")
    print(f"📡 [API请求] {url}")
    
    try:
        # 发送批量请求
        with urllib.request.urlopen(url, timeout=timeout) as response:
            xml_content = response.read().decode('utf-8')
        
        # 解析XML获取所有论文信息
        return parse_arxiv_batch_xml(xml_content, arxiv_ids)
        
    except Exception as e:
        print(f"❌ [批量查询] 批量请求失败: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'found_papers': [],
            'not_exist_ids': [],
            'error_ids': [{'arxiv_id': id, 'error': str(e)} for id in arxiv_ids]
        }

def parse_arxiv_batch_xml(xml_content: str, requested_ids: List[str]) -> Dict[str, Any]:
    """
    解析arXiv API返回的批量XML，提取所有论文信息
    
    Args:
        xml_content: arXiv API返回的XML内容
        requested_ids: 请求的arXiv ID列表
        
    Returns:
        包含所有论文信息的字典
    """
    try:
        root = ET.fromstring(xml_content)
        
        # 定义命名空间
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        # 查找所有entry元素
        entries = root.findall('atom:entry', namespaces)
        
        found_papers = []
        found_ids = set()
        
        print(f"🔍 [批量解析] 找到 {len(entries)} 个XML条目")
        
        for entry in entries:
            # 解析单个论文信息
            paper_info = parse_single_entry_xml(entry, namespaces)
            if paper_info and paper_info.get('arxiv_id'):
                found_papers.append(paper_info)
                found_ids.add(paper_info['arxiv_id'])
        
        # 确定哪些ID没有找到
        requested_ids_set = set(requested_ids)
        not_exist_ids = list(requested_ids_set - found_ids)
        
        print(f"✅ [批量解析] 成功: {len(found_papers)}篇，未找到: {len(not_exist_ids)}篇")
        
        return {
            'status': 'success',
            'found_papers': found_papers,
            'not_exist_ids': not_exist_ids,
            'error_ids': []
        }
        
    except Exception as e:
        print(f"❌ [批量解析] XML解析失败: {e}")
        return {
            'status': 'parse_error',
            'message': f'XML解析失败: {e}',
            'found_papers': [],
            'not_exist_ids': [],
            'error_ids': [{'arxiv_id': id, 'error': 'XML解析失败'} for id in requested_ids]
        }

def parse_single_entry_xml(entry, namespaces: Dict[str, str]) -> Dict[str, Any]:
    """
    解析单个XML entry元素，提取论文信息
    
    Args:
        entry: XML entry元素
        namespaces: XML命名空间字典
        
    Returns:
        包含论文信息的字典
    """
    try:
        # 提取基本信息
        paper_info = {}
        
        # 标题
        title_elem = entry.find('atom:title', namespaces)
        if title_elem is not None:
            paper_info['title'] = title_elem.text.strip().replace('\n', ' ')
        
        # arXiv ID
        id_elem = entry.find('atom:id', namespaces)
        if id_elem is not None:
            arxiv_url = id_elem.text
            clean_id = arxiv_url.split('/')[-1].replace('v1', '').replace('v2', '').replace('v3', '')
            paper_info['arxiv_id'] = clean_id
            paper_info['id'] = clean_id  # 兼容前端字段名
            paper_info['paper_id'] = None  # 智能搜索的文章没有数据库ID
        
        # 摘要 - 修改字段名为abstract以匹配数据库结构
        summary_elem = entry.find('atom:summary', namespaces)
        if summary_elem is not None:
            paper_info['abstract'] = summary_elem.text.strip().replace('\n', ' ')
        
        # 作者 - 转换为字符串格式，匹配数据库结构
        authors = []
        for author in entry.findall('atom:author', namespaces):
            name_elem = author.find('atom:name', namespaces)
            if name_elem is not None:
                authors.append(name_elem.text)
        paper_info['authors'] = ', '.join(authors) if authors else ''
        
        # 发布日期
        published_elem = entry.find('atom:published', namespaces)
        if published_elem is not None:
            paper_info['published'] = published_elem.text
        
        # 更新日期 - 解析为update_date字段
        updated_elem = entry.find('atom:updated', namespaces)
        if updated_elem is not None:
            paper_info['updated'] = updated_elem.text
            # 解析日期并格式化为YYYY-MM-DD格式
            try:
                # arXiv时间格式：2025-08-25T17:41:27Z
                dt = datetime.fromisoformat(updated_elem.text.replace('Z', '+00:00'))
                paper_info['update_date'] = dt.strftime('%Y-%m-%d')
                print(f"📅 [日期解析] {paper_info.get('arxiv_id', 'N/A')}: {updated_elem.text} -> {paper_info['update_date']}")
            except Exception as e:
                print(f"⚠️  [日期解析] 失败 {updated_elem.text}: {e}")
                paper_info['update_date'] = datetime.now().strftime('%Y-%m-%d')
        else:
            # 没有更新日期时使用今天
            paper_info['update_date'] = datetime.now().strftime('%Y-%m-%d')
        
        # 分类
        categories = []
        for category in entry.findall('atom:category', namespaces):
            term = category.get('term')
            if term:
                categories.append(term)
        paper_info['categories'] = categories
        
        # PDF链接 - 添加link字段以匹配数据库结构
        for link in entry.findall('atom:link', namespaces):
            if link.get('title') == 'pdf':
                paper_info['pdf_url'] = link.get('href')
                paper_info['link'] = link.get('href')  # 匹配数据库结构
                break
        
        # 如果没有找到PDF链接，使用arXiv主页链接
        if 'link' not in paper_info and 'arxiv_id' in paper_info:
            paper_info['link'] = f"https://arxiv.org/abs/{paper_info['arxiv_id']}"
        
        # 机构信息 - 智能搜索暂时不包含
        paper_info['author_affiliation'] = ''
        
        return paper_info
        
    except Exception as e:
        print(f"❌ [单条解析] 解析单个entry失败: {e}")
        return None

def fetch_arxiv_paper_info(arxiv_id: str, timeout: int = 10) -> Dict[str, Any]:
    """
    通过arXiv API获取单篇论文详细信息
    
    Args:
        arxiv_id: arXiv论文ID
        timeout: 请求超时时间（秒）
        
    Returns:
        包含状态和内容的字典
    """
    # 构建API URL
    base_url = "http://export.arxiv.org/api/query?"
    query = f"id:{arxiv_id}"
    params = {
        'search_query': query,
        'start': 0,
        'max_results': 1
    }
    
    url = base_url + urllib.parse.urlencode(params)
    
    try:
        # 发送请求
        with urllib.request.urlopen(url, timeout=timeout) as response:
            xml_content = response.read().decode('utf-8')
        
        # 检查是否找到论文
        if '<entry>' in xml_content and '</entry>' in xml_content:
            # 解析XML获取详细信息
            paper_info = parse_arxiv_xml(xml_content)
            
            if paper_info:
                return {
                    'status': 'found',
                    'paper_info': paper_info,
                    'raw_xml': xml_content,
                    'arxiv_id': arxiv_id
                }
            else:
                return {
                    'status': 'parse_error',
                    'message': 'XML解析失败',
                    'arxiv_id': arxiv_id
                }
        else:
            return {
                'status': 'not_exist',
                'message': '论文不存在',
                'arxiv_id': arxiv_id
            }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'arxiv_id': arxiv_id
        }

def batch_save_papers_to_db(found_papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量保存论文到数据库
    
    Args:
        found_papers: 从arXiv获取的论文信息列表
        
    Returns:
        更新了paper_id的论文信息列表
    """
    if not found_papers:
        return []
    
    print(f"💾 [批量保存] 开始批量保存 {len(found_papers)} 篇论文到数据库")
    
    try:
        today_str = datetime.now().strftime('%Y-%m-%d')  # 仅作为fallback
        
        # 1. 准备论文数据
        paper_rows = []
        for paper in found_papers:
            # 使用论文的实际更新日期，如果没有则使用今天
            update_date = paper.get('update_date', today_str)
            
            paper_row = {
                'arxiv_id': paper['arxiv_id'],
                'title': paper['title'],
                'authors': paper['authors'],
                'abstract': paper['abstract'],
                'link': paper['link'],
                'update_date': update_date,
                'primary_category': paper.get('categories', [''])[0] if paper.get('categories') else None,
                'author_affiliation': paper.get('author_affiliation', '')
            }
            paper_rows.append(paper_row)
        
        # 2. 批量upsert论文，获取arxiv_id -> paper_id映射
        arxiv_to_paper_id = db_repo.upsert_papers_bulk(paper_rows)
        print(f"✅ [批量保存] 论文批量upsert完成，共处理 {len(arxiv_to_paper_id)} 条")
        
        # 3. 收集所有分类
        all_categories = set()
        for paper in found_papers:
            if paper.get('categories'):
                all_categories.update(paper.get('categories', []))
        
        # 4. 批量upsert分类
        if all_categories:
            category_list = [cat for cat in all_categories if cat]
            name_to_category_id = db_repo.upsert_categories_bulk(category_list)
            print(f"✅ [批量保存] 分类批量upsert完成，共处理 {len(name_to_category_id)} 个分类")
            
            # 5. 准备论文-分类关联数据
            paper_category_pairs = []
            for paper in found_papers:
                arxiv_id = paper['arxiv_id']
                paper_id = arxiv_to_paper_id.get(arxiv_id)
                if paper_id and paper.get('categories'):
                    for category in paper.get('categories', []):
                        if category and category in name_to_category_id:
                            category_id = name_to_category_id[category]
                            paper_category_pairs.append((paper_id, category_id))
            
            # 6. 批量关联论文分类
            if paper_category_pairs:
                db_repo.upsert_paper_categories_bulk(paper_category_pairs)
                print(f"✅ [批量保存] 论文分类关联完成，共处理 {len(paper_category_pairs)} 个关联")
        
        # 7. 更新paper_id到found_papers中（保留原有的update_date）
        for paper in found_papers:
            paper['paper_id'] = arxiv_to_paper_id.get(paper['arxiv_id'])
            # 不要覆盖paper['update_date']，保持arXiv API返回的真实日期
        
        print(f"🎉 [批量保存] 批量保存全部完成！")
        return found_papers
        
    except Exception as e:
        print(f"❌ [批量保存] 批量保存失败: {e}")
        # 保存失败不影响返回结果，paper_id保持为None
        return found_papers

def smart_search_papers_optimized(text_content: str) -> Dict[str, Any]:
    """
    智能搜索论文：解析文本中的arXiv ID并批量获取论文信息（优化版）
    
    Args:
        text_content: 包含arXiv ID的文本内容
        
    Returns:
        包含搜索结果的详细信息
    """
    start_time = datetime.now()
    print(f"🔍 [智能搜索优化版] 开始处理智能搜索请求，文本长度: {len(text_content)} 字符")
    
    # 1. 提取arXiv ID
    arxiv_ids = extract_arxiv_ids(text_content)
    
    if not arxiv_ids:
        return {
            'success': False,
            'message': '未在文本中找到任何arXiv ID',
            'articles': [],
            'total': 0,
            'performance': {
                'total_time': 0,
                'total_processed': 0,
                'found_count': 0,
                'not_exist_count': 0,
                'error_count': 0
            },
            'not_exist_ids': [],
            'error_details': []
        }
    
    print(f"📋 [智能搜索优化版] 提取到 {len(arxiv_ids)} 个arXiv ID: {arxiv_ids}")
    
    # 2. 批量获取论文信息（一次API调用）
    batch_start = datetime.now()
    batch_result = fetch_arxiv_papers_batch(arxiv_ids)
    batch_end = datetime.now()
    api_time = (batch_end - batch_start).total_seconds()
    
    print(f"⏱️  [API性能] 批量API调用完成，耗时: {api_time:.2f}s")
    
    if batch_result['status'] != 'success':
        return {
            'success': False,
            'message': batch_result.get('message', '批量获取论文信息失败'),
            'articles': [],
            'total': 0,
            'performance': {
                'total_time': api_time,
                'total_processed': len(arxiv_ids),
                'found_count': 0,
                'not_exist_count': 0,
                'error_count': len(arxiv_ids)
            },
            'not_exist_ids': [],
            'error_details': batch_result.get('error_ids', [])
        }
    
    # 3. 批量保存到数据库
    db_start = datetime.now()
    found_papers = batch_save_papers_to_db(batch_result['found_papers'])
    db_end = datetime.now()
    db_time = (db_end - db_start).total_seconds()
    
    print(f"⏱️  [DB性能] 批量数据库操作完成，耗时: {db_time:.2f}s")
    
    # 4. 计算统计信息
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    found_count = len(found_papers)
    not_exist_count = len(batch_result['not_exist_ids'])
    error_count = len(batch_result['error_ids'])
    
    print(f"✅ [智能搜索优化版] 搜索完成，耗时: {total_time:.2f}s")
    print(f"   📊 统计: 总计{len(arxiv_ids)}篇，成功{found_count}篇，失败{not_exist_count}篇，错误{error_count}篇")
    print(f"   ⚡ 性能: API调用{api_time:.2f}s + DB操作{db_time:.2f}s")
    
    # 构建与search_articles一致的返回结构
    return {
        'success': True,
        'articles': found_papers,
        'total': found_count,
        'search_type': 'smart_search_optimized',
        'performance': {
            'total_time': round(total_time, 2),
            'api_time': round(api_time, 2),
            'db_time': round(db_time, 2),
            'total_processed': len(arxiv_ids),
            'found_count': found_count,
            'not_exist_count': not_exist_count,
            'error_count': error_count
        },
        'not_exist_ids': batch_result['not_exist_ids'],
        'error_details': batch_result['error_ids'],
        'message': f'智能搜索完成，成功获取 {found_count} 篇论文信息'
    }

def smart_search_papers(text_content: str, delay: float = None) -> Dict[str, Any]:
    """
    智能搜索论文：解析文本中的arXiv ID并批量获取论文信息
    保留原函数名以保持向后兼容性，内部调用优化版本
    
    Args:
        text_content: 包含arXiv ID的文本内容
        delay: 请求间延迟（秒，优化版本中已忽略）
        
    Returns:
        包含搜索结果的详细信息
    """
    return smart_search_papers_optimized(text_content)