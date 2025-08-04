#!/usr/bin/env python3
"""
使用本地GROBID Docker服务解析PDF文件，提取作者机构信息

输入：ArXiv论文链接
输出：去重的作者机构列表
"""

import requests
import re
import sys
import xml.etree.ElementTree as ET
import grobid_tei_xml
from typing import List

# 本地GROBID Docker服务URL
GROBID_SERVER_URL = "http://localhost:8070"

def extract_arxiv_id_from_url(url: str) -> str:
    """
    从arxiv abstract URL中提取arxiv_id
    例如: http://arxiv.org/abs/2507.23785v1 -> 2507.23785v1
    """
    url = url.strip()
    pattern = r'/abs/([^/\s]+)/?$'
    match = re.search(pattern, url)
    
    if match:
        return match.group(1)
    else:
        raise ValueError(f"无法从URL中提取arxiv_id: {url}")

def download_arxiv_pdf(arxiv_url: str) -> bytes:
    """
    从ArXiv URL下载PDF文件
    """
    arxiv_id = extract_arxiv_id_from_url(arxiv_url)
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    
    response = requests.get(pdf_url, timeout=30)
    response.raise_for_status()
    
    return response.content

def process_pdf_with_grobid(pdf_content: bytes, timeout: int = 60) -> str:
    """
    使用本地GROBID Docker服务处理PDF文件，返回TEI-XML
    """
    grobid_url = f"{GROBID_SERVER_URL}/api/processFulltextDocument"
    
    files = {
        'input': ('paper.pdf', pdf_content, 'application/pdf')
    }
    
    data = {
        'consolidateHeader': '1',
        'includeRawAffiliations': '1'
    }
    
    response = requests.post(
        grobid_url,
        files=files,
        data=data,
        timeout=timeout
    )
    
    response.raise_for_status()
    return response.text

def parse_grobid_xml(xml_content: str) -> List[str]:
    """
    解析GROBID返回的TEI-XML，提取去重的机构信息列表
    """
    affiliations = set()
    
    try:
        # 使用grobid_tei_xml库解析
        doc = grobid_tei_xml.parse_document_xml(xml_content)
        
        # 从作者信息中提取机构
        if doc.header.authors:
            for author in doc.header.authors:
                if hasattr(author, 'affiliation') and author.affiliation:
                    if hasattr(author.affiliation, 'institution') and author.affiliation.institution:
                        institution = author.affiliation.institution.strip()
                        if institution:
                            affiliations.add(institution)
        
        # 从XML中提取原始机构信息（备用方法）
        try:
            root = ET.fromstring(xml_content)
            namespaces = {'tei': 'http://www.tei-c.org/ns/1.0'}
            affil_elements = root.findall('.//tei:affiliation', namespaces)
            
            for affil in affil_elements:
                # 优先查找orgName标签
                org_names = affil.findall('.//tei:orgName', namespaces)
                for org in org_names:
                    org_text = ''.join(org.itertext()).strip()
                    if org_text and len(org_text) > 5:
                        clean_org = re.sub(r'\d+', '', org_text).strip()
                        if clean_org:
                            affiliations.add(clean_org)
                
                # 如果没有orgName，提取完整文本
                if not org_names:
                    affil_text = ''.join(affil.itertext()).strip()
                    clean_text = re.sub(r'\d+', '', affil_text).strip()
                    clean_text = re.sub(r'\s+', ' ', clean_text)
                    if clean_text and 10 < len(clean_text) < 200:
                        affiliations.add(clean_text)
                        
        except Exception:
            pass
        
    except Exception:
        pass
    
    return list(affiliations)

def get_author_affiliations(arxiv_url: str) -> List[str]:
    """
    从ArXiv论文链接获取作者机构信息列表（去重）
    
    Args:
        arxiv_url: ArXiv论文链接，如 http://arxiv.org/abs/2507.23785v1
        
    Returns:
        List[str]: 去重的作者机构列表
        
    Raises:
        Exception: 当处理失败时抛出异常
    """
    # 下载PDF
    pdf_content = download_arxiv_pdf(arxiv_url)
    
    # 使用GROBID处理
    xml_content = process_pdf_with_grobid(pdf_content)
    
    # 解析并返回机构列表
    return parse_grobid_xml(xml_content)

if __name__ == "__main__":
    # 简单的测试用例
    if len(sys.argv) < 2:
        print("使用方法: python parse_author_org_v3.py <arxiv_url>")
        print("例如: python parse_author_org_v3.py http://arxiv.org/abs/2507.23785v1")
        exit(1)
    
    arxiv_url = sys.argv[1]
    try:
        affiliations = get_author_affiliations(arxiv_url)
        print(f"论文链接: {arxiv_url}")
        print(f"作者机构 ({len(affiliations)}):")
        for i, affil in enumerate(affiliations, 1):
            print(f"  {i}. {affil}")
    except Exception as e:
        print(f"错误: {e}")