#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time

def analyze_paper(client, system_prompt, title, abstract, max_retries=3):
    """分析单篇论文"""
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