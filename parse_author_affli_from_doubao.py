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
    从ArXiv URL下载PDF文件（高度优化性能）
    """
    arxiv_id = extract_arxiv_id_from_url(arxiv_url)
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    
    print(f"[PDF下载] 开始下载: {pdf_url}")
    start_time = __import__('time').time()
    
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
    
        end_time = __import__('time').time()
        size_mb = len(pdf_content) / (1024 * 1024)
        speed_mbps = size_mb / (end_time - start_time) if (end_time - start_time) > 0 else 0
        print(f"[PDF下载] 完成，大小: {size_mb:.1f}MB，耗时: {end_time - start_time:.2f}s (速度: {speed_mbps:.1f}MB/s)")
        
        return bytes(pdf_content)


def extract_first_page_text(pdf_content: bytes) -> str:
    """
    提取PDF第一页的文本内容（优化性能）
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


# 添加简单的内存缓存
_AFFILIATION_CACHE = {}

def clear_affiliation_cache():
    """清空机构信息缓存"""
    global _AFFILIATION_CACHE
    _AFFILIATION_CACHE.clear()
    print("[缓存] 🗑️ 机构信息缓存已清空")

def get_author_affiliations(arxiv_url: str, use_cache: bool = True, progress_callback=None) -> List[str]:
    """
    从ArXiv论文链接获取作者机构信息列表（去重）
    
    Args:
        arxiv_url: ArXiv论文链接，如 http://arxiv.org/abs/2507.23785v1
        use_cache: 是否使用缓存
        
    Returns:
        List[str]: 去重的作者机构列表
        
    Raises:
        Exception: 当处理失败时抛出异常
    """
    import time
    total_start = time.time()
    
    print(f"[机构获取] 开始处理: {arxiv_url}")
    
    # 检查缓存
    if use_cache and arxiv_url in _AFFILIATION_CACHE:
        cached_result = _AFFILIATION_CACHE[arxiv_url]
        print(f"[机构获取] 🚀 使用缓存结果，机构数: {len(cached_result)}")
        return cached_result
    
    try:
        # 调用进度回调
        if progress_callback:
            progress_callback("分析后已选中该论文，正在下载PDF获取机构信息，需要10s左右...")
        
        # 1. 下载PDF（优化：并行处理）
        step_start = time.time()
        pdf_content = download_arxiv_pdf(arxiv_url)
        download_time = time.time() - step_start
        print(f"[机构获取] PDF下载完成，耗时: {download_time:.2f}s")
        
        # 调用进度回调
        if progress_callback:
            progress_callback("分析后已选中改论文，正在解析PDF文本...")
        
        # 2. 提取第一页文本（优化：只提取前2000字符用于机构识别）
        step_start = time.time()
        first_page_text = extract_first_page_text(pdf_content)
        
        # 优化：只取前2000字符，通常机构信息都在论文开头
        if len(first_page_text) > 2000:
            first_page_text = first_page_text[:2000] + "\n[文本已截断，仅保留前2000字符]"
            print(f"[机构获取] ✂️ 文本已截断至2000字符以优化处理速度")
        
        extract_time = time.time() - step_start
        print(f"[机构获取] PDF解析完成，耗时: {extract_time:.2f}s，文本长度: {len(first_page_text)}")
        
        # 调用进度回调
        if progress_callback:
            progress_callback("分析后已选中该论文，正在调用AI模型分析机构信息...")
        
        # 3. 使用豆包API解析机构信息
        step_start = time.time()
        affiliations = parse_affiliations_with_doubao(first_page_text)
        api_time = time.time() - step_start
        print(f"[机构获取] 豆包API分析完成，耗时: {api_time:.2f}s，找到机构: {len(affiliations)}")
        
        # 4. 去重并返回
        unique_affiliations = []
        for affil in affiliations:
            if affil not in unique_affiliations:
                unique_affiliations.append(affil)
        
        # 缓存结果
        if use_cache:
            _AFFILIATION_CACHE[arxiv_url] = unique_affiliations
            print(f"[机构获取] 💾 结果已缓存")
        
        total_time = time.time() - total_start
        print(f"[机构获取] 全流程完成，总耗时: {total_time:.2f}s (下载:{download_time:.1f}s, 解析:{extract_time:.1f}s, API:{api_time:.1f}s)，最终机构数: {len(unique_affiliations)}")
        
        return unique_affiliations
        
    except Exception as e:
        print(f"[机构获取] ❌ 处理失败: {e}")
        # 对于某些错误（如文件过大），不缓存结果，允许后续重试
        error_msg = str(e)
        should_cache_failure = False
        
        # 只有网络错误等临时性问题才缓存失败结果
        if "网络" in error_msg or "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            should_cache_failure = True
            
        if use_cache and should_cache_failure:
            _AFFILIATION_CACHE[arxiv_url] = []
            print(f"[机构获取] 💾 失败结果已缓存（临时性错误）")
        else:
            print(f"[机构获取] 🚫 失败结果未缓存（允许重试）")
            
        raise e


if __name__ == "__main__":
    # 简单的测试用例
    if len(sys.argv) < 2:
        print("使用方法: python parse_author_affli_from_doubao.py <arxiv_url>")
        print("例如: python parse_author_affli_from_doubao.py \"http://arxiv.org/abs/2507.23785v1\"")
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