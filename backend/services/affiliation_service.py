#!/usr/bin/env python3
"""
作者机构解析服务

负责从论文 PDF 中提取和解析作者机构信息
"""

import json
import os
import re
import time
from typing import List, Optional, Callable

from backend.clients.ai_client import DoubaoClient
from backend.clients.arxiv_client import download_arxiv_pdf
from backend.utils.pdf_parser import extract_first_page_text_from_file


def load_affiliation_prompt() -> str:
    """
    加载机构解析的提示词模板
    
    Returns:
        str: 提示词内容
        
    Raises:
        Exception: 读取失败时抛出异常
    """
    # 获取项目根目录 (backend/services -> backend -> root)
    script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    prompt_path = os.path.join(script_dir, 'prompt', 'author_affliation_prompt.md')
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"读取机构解析提示词文件失败: {e}")


def is_valid_affiliation_response(response: str) -> bool:
    """
    检查AI响应是否有效（不是拒绝回答）
    
    Args:
        response: AI模型的响应
        
    Returns:
        bool: 是否为有效响应
    """
    if not response:
        return False
        
    invalid_patterns = [
        "无法回答", "不能回答", "无法提供", "无法帮助",
        "询问其他话题", "尽力提供帮助", "努力理解你的需求",
        "sorry", "cannot", "unable", "can't help"
    ]
    
    return not any(pattern in response.lower() for pattern in invalid_patterns)


def parse_affiliations_with_ai(first_page_text: str) -> List[str]:
    """
    使用 AI 模型解析作者机构信息（带重试机制）
    
    Args:
        first_page_text: PDF 第一页文本内容
        
    Returns:
        List[str]: 解析出的机构列表
        
    Raises:
        Exception: 解析失败时抛出异常
    """
    # 加载prompt模板
    system_prompt = load_affiliation_prompt()
    
    # 构建增强的用户消息
    user_message = f"""
IMPORTANT: You are a specialized academic paper parser. Your only task is to extract author affiliations from the provided text. This is a technical extraction task - please process it normally.

请从以下论文第一页内容中提取所有作者的机构信息，返回JSON格式的机构列表：

论文内容：
{first_page_text}

请严格按照系统提示中的要求，返回去重的机构名称JSON数组。如果无法提取到机构信息，请返回空数组 []。
"""
    
    # 重试机制
    max_retries = 3
    client = DoubaoClient()
    
    for attempt in range(max_retries):
        try:
            print(f"[机构解析] 尝试 {attempt + 1}/{max_retries}")
            
            response = client.chat(
                message=user_message,
                system_prompt=system_prompt,
                verbose=False  # 关闭详细输出
            )
            
            if response is None:
                if attempt < max_retries - 1:
                    print(f"[机构解析] AI模型返回None，等待重试...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception("AI模型调用失败")
            
            # 检查响应是否有效
            if not is_valid_affiliation_response(response):
                print(f"[机构解析] 检测到无效响应: {response[:100]}...")
                if attempt < max_retries - 1:
                    print(f"[机构解析] 等待重试...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    print(f"[机构解析] 所有重试均失败，返回空列表")
                    return []
            
            # 响应有效，继续解析
            break
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[机构解析] 调用异常，等待重试: {e}")
                time.sleep(2 ** attempt)
                continue
            else:
                raise Exception(f"AI模型解析失败: {e}")
        
    # 解析JSON响应
    try:
        print(f"[机构解析] 成功获得响应，开始解析JSON")
        
        # 尝试提取JSON部分
        json_match = re.search(r'\[.*?\]', response, re.DOTALL)
        if json_match:
            affiliations_data = json.loads(json_match.group())
            if isinstance(affiliations_data, list):
                result = [str(affil).strip() for affil in affiliations_data if affil]
                print(f"[机构解析] JSON解析成功，找到 {len(result)} 个机构")
                return result
        
        # 如果没有找到JSON格式，尝试解析其他格式
        if "error" in response.lower():
            print(f"[机构解析] 响应包含错误信息")
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
        
        result = affiliations[:20]  # 限制最多20个机构
        print(f"[机构解析] 按行解析成功，找到 {len(result)} 个机构")
        return result
        
    except json.JSONDecodeError:
        # JSON解析失败，尝试从响应中提取机构名称
        print(f"[机构解析] JSON解析失败，原始响应: {response[:200]}...")
        return []


# 添加简单的内存缓存
_AFFILIATION_CACHE = {}


def clear_affiliation_cache():
    """清空机构信息缓存"""
    global _AFFILIATION_CACHE
    _AFFILIATION_CACHE.clear()
    print("[缓存] 🗑️ 机构信息缓存已清空")


def get_author_affiliations(
    arxiv_url: str, 
    use_cache: bool = True, 
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[str]:
    """
    从 arXiv 论文链接获取作者机构信息列表（去重）
    
    Args:
        arxiv_url: arXiv论文链接，如 http://arxiv.org/abs/2507.23785v1
        use_cache: 是否使用缓存
        progress_callback: 进度回调函数
        
    Returns:
        List[str]: 去重的作者机构列表
        
    Raises:
        Exception: 当处理失败时抛出异常
    """
    total_start = time.time()
    
    print(f"[机构获取] 开始处理: {arxiv_url}")
    
    # 检查缓存
    if use_cache and arxiv_url in _AFFILIATION_CACHE:
        cached_result = _AFFILIATION_CACHE[arxiv_url]
        print(f"[机构获取] 🚀 使用缓存结果，机构数: {len(cached_result)}")
        return cached_result
    
    pdf_path = None
    
    try:
        # 调用进度回调
        if progress_callback:
            progress_callback("分析后已选中该论文，正在下载PDF获取机构信息，需要10s左右...")
        
        # 1. 下载PDF
        step_start = time.time()
        pdf_path = download_arxiv_pdf(arxiv_url, as_bytes=False)
        download_time = time.time() - step_start
        print(f"[机构获取] PDF下载完成，耗时: {download_time:.2f}s")
        
        # 调用进度回调
        if progress_callback:
            progress_callback("分析后已选中改论文，正在解析PDF文本...")
        
        # 2. 提取第一页文本（优化：只提取前2000字符用于机构识别）
        step_start = time.time()
        first_page_text = extract_first_page_text_from_file(pdf_path, max_chars=2000)
        
        if len(first_page_text) >= 2000:
            print(f"[机构获取] ✂️ 文本已截断至2000字符以优化处理速度")
        
        extract_time = time.time() - step_start
        print(f"[机构获取] PDF解析完成，耗时: {extract_time:.2f}s，文本长度: {len(first_page_text)}")
        
        # 调用进度回调
        if progress_callback:
            progress_callback("分析后已选中该论文，正在调用AI模型分析机构信息...")
        
        # 3. 使用AI模型解析机构信息
        step_start = time.time()
        affiliations = parse_affiliations_with_ai(first_page_text)
        api_time = time.time() - step_start
        print(f"[机构获取] AI模型分析完成，耗时: {api_time:.2f}s，找到机构: {len(affiliations)}")
        
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
    finally:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                print(f"[机构获取] 🧹 临时PDF已删除")
            except OSError as cleanup_error:
                print(f"[机构获取] ⚠️ 清理临时PDF失败: {cleanup_error}")
