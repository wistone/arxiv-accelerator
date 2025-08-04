#!/usr/bin/env python3
"""
使用豆包API解析ArXiv论文作者机构信息

输入：ArXiv论文链接
输出：去重的作者机构列表

该方案使用大模型智能解析论文第一页内容，能够处理各种复杂的论文格式。
"""

import requests
import re
import sys
import json
import io
from typing import List
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from doubao_client import DoubaoClient


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


def extract_first_page_text(pdf_content: bytes) -> str:
    """
    提取PDF第一页的文本内容
    """
    laparams = LAParams()
    output = io.StringIO()
    
    try:
        extract_text_to_fp(
            io.BytesIO(pdf_content),
            output,
            laparams=laparams,
            maxpages=1,  # 只提取第一页
            page_numbers=[0],
            codec='utf-8'
        )
        return output.getvalue()
    except Exception as e:
        raise Exception(f"PDF文本提取失败: {e}")


def load_prompt_template() -> str:
    """
    加载prompt模板
    """
    import os
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, 'prompt', 'author_affliation_prompt.md')
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"读取prompt文件失败: {e}")


def parse_affiliations_with_doubao(first_page_text: str) -> List[str]:
    """
    使用豆包API解析作者机构信息
    """
    # 加载prompt模板
    system_prompt = load_prompt_template()
    
    # 构建用户消息
    user_message = f"""
请从以下论文第一页内容中提取所有作者的机构信息，返回JSON格式的机构列表：

论文内容：
{first_page_text}

请严格按照系统提示中的要求，返回去重的机构名称JSON数组。
"""
    
    # 调用豆包API
    try:
        client = DoubaoClient()
        response = client.chat(
            message=user_message,
            system_prompt=system_prompt,
            verbose=False  # 关闭详细输出
        )
        
        if response is None:
            raise Exception("豆包API调用失败")
        
        # 解析JSON响应
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                affiliations_data = json.loads(json_match.group())
                if isinstance(affiliations_data, list):
                    return [str(affil).strip() for affil in affiliations_data if affil]
            
            # 如果没有找到JSON格式，尝试解析其他格式
            if "error" in response.lower():
                return []
            
            # 尝试按行解析
            lines = response.strip().split('\n')
            affiliations = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('```'):
                    # 移除列表标记
                    clean_line = re.sub(r'^\d+\.\s*|^-\s*|^\*\s*', '', line).strip()
                    if clean_line and len(clean_line) > 2:
                        affiliations.append(clean_line)
            
            return affiliations[:20]  # 限制最多20个机构
            
        except json.JSONDecodeError:
            # JSON解析失败，尝试从响应中提取机构名称
            print(f"JSON解析失败，原始响应: {response}")
            return []
            
    except Exception as e:
        raise Exception(f"豆包API解析失败: {e}")


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
    
    # 提取第一页文本
    first_page_text = extract_first_page_text(pdf_content)
    
    # 使用豆包API解析机构信息
    affiliations = parse_affiliations_with_doubao(first_page_text)
    
    # 去重并返回
    unique_affiliations = []
    for affil in affiliations:
        if affil not in unique_affiliations:
            unique_affiliations.append(affil)
    
    return unique_affiliations


if __name__ == "__main__":
    # 简单的测试用例
    if len(sys.argv) < 2:
        print("使用方法: python parse_author_org_v4.py <arxiv_url>")
        print("例如: python parse_author_org_v4.py http://arxiv.org/abs/2507.23785v1")
        exit(1)
    
    arxiv_url = sys.argv[1]
    try:
        print(f"正在处理论文: {arxiv_url}")
        affiliations = get_author_affiliations(arxiv_url)
        print(f"论文链接: {arxiv_url}")
        print(f"作者机构 ({len(affiliations)}):")
        for i, affil in enumerate(affiliations, 1):
            print(f"  {i}. {affil}")
    except Exception as e:
        print(f"错误: {e}")