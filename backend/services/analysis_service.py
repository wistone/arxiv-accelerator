#!/usr/bin/env python3
"""
论文分析服务

提供论文的AI智能分析功能
"""

import json
import time
from typing import Dict, Any, Optional


def analyze_paper(client, system_prompt: str, title: str, abstract: str, max_retries: int = 3) -> str:
    """
    分析单篇论文
    
    Args:
        client: AI客户端实例
        system_prompt: 系统提示词
        title: 论文标题
        abstract: 论文摘要
        max_retries: 最大重试次数
        
    Returns:
        str: JSON格式的分析结果
    """
    for attempt in range(max_retries):
        try:
            print(f"开始分析论文 (第{attempt+1}/{max_retries}次尝试): {title[:50]}...")
            
            # 构建user prompt
            user_prompt = f"Title: {title}\nAbstract: {abstract}"
            
            print("正在调用AI模型...")
            start_time = time.time()
            
            response = client.chat(
                message=user_prompt,
                system_prompt=system_prompt,
                verbose=True  # 启用详细输出以便在Render中查看模型调用日志
            )
            
            elapsed_time = time.time() - start_time
            print(f"AI模型响应完成，耗时: {elapsed_time:.2f}秒，响应长度: {len(response) if response else 0}")
            
            if response:
                try:
                    # 尝试解析JSON
                    parsed_json = json.loads(response)
                    # 返回紧凑的JSON字符串
                    result = json.dumps(parsed_json, ensure_ascii=False, separators=(',', ':'))
                    print(f"✅ JSON解析成功: {result[:100]}...")
                    return result
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    if attempt < max_retries - 1:
                        print(f"⏭️  将重试...")
                        time.sleep(2 ** attempt)  # 指数退避
                        continue
                    else:
                        error_result = f'{{"error": "JSON parsing failed after {max_retries} attempts: {str(e)}"}}'
                        print(f"返回错误结果: {error_result}")
                        return error_result
            else:
                print(f"❌ 模型调用失败 (第{attempt+1}次)")
                if attempt < max_retries - 1:
                    print(f"⏭️  将重试...")
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                else:
                    error_result = f'{{"error": "Model call failed after {max_retries} attempts"}}'
                    print(f"返回错误结果: {error_result}")
                    return error_result
                    
        except Exception as e:
            print(f"❌ 分析过程中出现错误 (第{attempt+1}次): {e}")
            if attempt < max_retries - 1:
                print(f"⏭️  将重试...")
                time.sleep(2 ** attempt)  # 指数退避
                continue
            else:
                error_result = f'{{"error": "Analysis error after {max_retries} attempts: {str(e)}"}}'
                print(f"异常处理返回: {error_result}")
                return error_result
    
    # 不应该到达这里，但以防万一
    return '{"error": "Unexpected error in analyze_paper"}'


def parse_analysis_result(result_json: str) -> Dict[str, Any]:
    """
    解析分析结果JSON
    
    Args:
        result_json: JSON格式的分析结果
        
    Returns:
        Dict: 解析后的结果字典
    """
    try:
        return json.loads(result_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"}


def validate_analysis_result(result: Dict[str, Any]) -> bool:
    """
    验证分析结果的有效性
    
    Args:
        result: 分析结果字典
        
    Returns:
        bool: 是否有效
    """
    required_fields = ["pass_filter"]
    return all(field in result for field in required_fields)


def calculate_normalized_score(raw_score: int, max_score: int = 15) -> int:
    """
    计算标准化分数
    
    Args:
        raw_score: 原始分数
        max_score: 最大分数
        
    Returns:
        int: 标准化分数 (0-10)
    """
    return min(10, raw_score) if raw_score >= 0 else 0
