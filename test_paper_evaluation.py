#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from doubao_client import DoubaoClient

def read_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"读取文件 {file_path} 失败: {e}")
        return None

def test_paper_evaluation():
    """测试论文评估功能"""
    
    print("=" * 80)
    print("论文评估测试 - 使用System Prompt和User Prompt")
    print("=" * 80)
    
    # 读取system prompt和user prompt
    system_prompt = read_file_content("prompt/system_prompt.md")
    user_prompt = read_file_content("prompt/test1-user_prompt.md")
    
    if not system_prompt or not user_prompt:
        print("无法读取prompt文件，测试终止")
        return
        
    print(f"System Prompt长度: {len(system_prompt)} 字符")
    print(f"User Prompt长度: {len(user_prompt)} 字符")
    print("-" * 50)
    
    # 创建doubao客户端
    client = DoubaoClient()
    
    # 调用模型进行论文评估
    try:
        response = client.chat(
            message=user_prompt,
            system_prompt=system_prompt,
            verbose=True
        )
        
        if response:
            print("\n" + "=" * 80)
            print("模型评估结果:")
            print("=" * 80)
            print(response)
            print("=" * 80)
            
            # 尝试解析JSON
            try:
                import json
                parsed_json = json.loads(response)
                print("\nJSON解析成功:")
                print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
            except json.JSONDecodeError as e:
                print(f"\nJSON解析失败: {e}")
                print("原始回复可能包含额外文本")
        else:
            print("模型调用失败")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_paper_evaluation()