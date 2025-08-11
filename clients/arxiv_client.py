#!/usr/bin/env python3
"""
arXiv 客户端

负责与 arXiv 服务的网络交互，包括 PDF 下载等
"""

import requests
import time
from typing import Tuple

from utils.pdf_parser import extract_arxiv_id_from_url


def download_arxiv_pdf(arxiv_url: str) -> bytes:
    """
    从 arXiv URL 下载 PDF 文件（高度优化性能）
    
    Args:
        arxiv_url: arXiv 论文链接
        
    Returns:
        bytes: PDF 文件内容
        
    Raises:
        Exception: 下载失败时抛出异常
    """
    arxiv_id = extract_arxiv_id_from_url(arxiv_url)
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    
    print(f"[PDF下载] 开始下载: {pdf_url}")
    start_time = time.time()
    
    # 高性能下载配置
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/pdf',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip, deflate'  # 启用压缩
    }
    
    # 使用session复用连接，设置更积极的超时
    with requests.Session() as session:
        session.headers.update(headers)
        
        # 1. 先HEAD请求检查文件大小，用于日志记录
        try:
            head_response = session.head(pdf_url, timeout=5)
            content_length = head_response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                print(f"[PDF下载] 预检文件大小: {size_mb:.1f}MB")
        except Exception as e:
            print(f"[PDF下载] ⚠️  预检失败，继续下载: {e}")
        
        # 2. 流式下载，设置较短超时
        response = session.get(pdf_url, timeout=10, stream=True)  # 进一步缩短超时
        response.raise_for_status()
        
        # 3. 分块下载（无大小限制）
        pdf_content = bytearray()
        
        for chunk in response.iter_content(chunk_size=8192):  # 8KB块
            if chunk:
                pdf_content.extend(chunk)
    
        end_time = time.time()
        size_mb = len(pdf_content) / (1024 * 1024)
        speed_mbps = size_mb / (end_time - start_time) if (end_time - start_time) > 0 else 0
        print(f"[PDF下载] 完成，大小: {size_mb:.1f}MB，耗时: {end_time - start_time:.2f}s (速度: {speed_mbps:.1f}MB/s)")
        
        return bytes(pdf_content)


def get_paper_metadata(arxiv_id: str) -> dict:
    """
    获取论文元数据
    
    Args:
        arxiv_id: arXiv ID
        
    Returns:
        dict: 论文元数据
    """
    # TODO: 实现从 arXiv API 获取元数据的功能
    return {
        "arxiv_id": arxiv_id,
        "title": "",
        "authors": [],
        "abstract": "",
        "categories": []
    }
