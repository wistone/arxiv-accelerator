#!/usr/bin/env python3
"""
arXiv 客户端

负责与 arXiv 服务的网络交互，包括 PDF 下载等
"""

import requests
import time
from typing import Tuple

from backend.utils.pdf_parser import extract_arxiv_id_from_url


def download_arxiv_pdf(arxiv_url: str) -> bytes:
    """
    从 arXiv URL 下载 PDF 文件（内存优化版本）
    
    Args:
        arxiv_url: arXiv 论文链接
        
    Returns:
        bytes: PDF 文件内容
        
    Raises:
        Exception: 下载失败时抛出异常
    """
    from backend.utils.memory_manager import StreamBuffer, monitor_memory
    
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
        
        # 1. 先HEAD请求检查文件大小，用于内存管理决策
        content_length = None
        try:
            head_response = session.head(pdf_url, timeout=5)
            content_length = head_response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                print(f"[PDF下载] 预检文件大小: {size_mb:.1f}MB")
                
                # 大文件预警
                if size_mb > 20:
                    print(f"⚠️ [PDF下载] 文件过大({size_mb:.1f}MB)，可能导致内存不足")
                    
        except Exception as e:
            print(f"[PDF下载] ⚠️  预检失败，继续下载: {e}")
        
        # 2. 使用智能缓冲区下载
        buffer = StreamBuffer(max_size=15 * 1024 * 1024)  # 15MB内存限制
        
        response = session.get(pdf_url, timeout=15, stream=True)  
        response.raise_for_status()
        
        # 3. 内存友好的分块下载
        total_size = 0
        for chunk in response.iter_content(chunk_size=32768):  # 32KB块，减少内存碎片
            if chunk:
                buffer.write(chunk)
                total_size += len(chunk)
                
                # 内存压力检查
                if total_size > 20 * 1024 * 1024:  # 超过20MB时检查内存
                    from backend.utils.memory_manager import memory_manager
                    pressure = memory_manager.check_memory_pressure()
                    if pressure == 'critical':
                        raise Exception(f"内存压力过高，终止下载。已下载: {total_size/1024/1024:.1f}MB")
        
        pdf_content = buffer.get_content()
        
        end_time = time.time()
        size_mb = len(pdf_content) / (1024 * 1024)
        speed_mbps = size_mb / (end_time - start_time) if (end_time - start_time) > 0 else 0
        print(f"[PDF下载] 完成，大小: {size_mb:.1f}MB，耗时: {end_time - start_time:.2f}s (速度: {speed_mbps:.1f}MB/s)")
        
        return pdf_content


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
