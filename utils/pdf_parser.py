#!/usr/bin/env python3
"""
PDF 解析工具

提供高性能的 PDF 文本提取功能
"""

import io
import re
from typing import List
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams


def extract_arxiv_id_from_url(url: str) -> str:
    """
    从 arXiv 链接中提取 arXiv ID
    
    Args:
        url: arXiv 论文链接
        
    Returns:
        str: arXiv ID (如 2507.23785v1)
        
    Raises:
        ValueError: 无法解析时抛出异常
    """
    url = url.strip()
    pattern = r'/abs/([^/\s]+)/?$'
    match = re.search(pattern, url)
    
    if match:
        return match.group(1)
    else:
        raise ValueError(f"无法从URL中提取arxiv_id: {url}")


def extract_first_page_text(pdf_content: bytes, max_chars: int = 2000) -> str:
    """
    提取 PDF 第一页的文本内容（优化性能）
    
    Args:
        pdf_content: PDF 文件内容
        max_chars: 最大字符数
        
    Returns:
        str: 提取的文本内容
        
    Raises:
        Exception: PDF解析失败时抛出异常
    """
    # 优化LAParams参数以提高速度
    laparams = LAParams(
        word_margin=0.1,
        char_margin=2.0,
        line_margin=0.5,
        boxes_flow=0.5,
        all_texts=False  # 跳过一些不必要的文本处理
    )
    output = io.StringIO()
    
    try:
        # 增加超时和错误抑制
        import logging
        logging.getLogger('pdfminer').setLevel(logging.ERROR)  # 抑制警告信息
        
        extract_text_to_fp(
            io.BytesIO(pdf_content),
            output,
            laparams=laparams,
            maxpages=1,  # 只提取第一页
            page_numbers=[0],
            codec='utf-8',
            caching=True,  # 启用缓存
            check_extractable=True
        )
        
        text = output.getvalue()
        
        # 截断到指定长度
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[文本已截断，优化处理速度]"
            
        return text
        
    except Exception as e:
        raise Exception(f"PDF文本提取失败: {e}")


def clean_extracted_text(text: str) -> str:
    """
    清理提取的文本内容
    
    Args:
        text: 原始文本
        
    Returns:
        str: 清理后的文本
    """
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 移除特殊字符
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\"\'\/]', '', text)
    
    return text.strip()
