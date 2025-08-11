#!/usr/bin/env python3
"""
AI 模型客户端 - 统一的 AI 服务接口

支持豆包 (Doubao) 等多种 AI 模型的调用
"""

import os
from openai import OpenAI

# 加载环境变量文件
try:
    from dotenv import load_dotenv
    load_dotenv()  # 加载.env文件中的环境变量
except ImportError:
    pass  # 如果没有dotenv，继续使用系统环境变量


class DoubaoClient:
    """
    豆包 (Doubao) AI 模型客户端
    
    提供论文分析、文本理解等 AI 能力
    """
    
    def __init__(self, api_key=None, model=None):
        """
        初始化豆包客户端
        
        Args:
            api_key (str, optional): API密钥，如果未提供则从环境变量DOUBAO_API_KEY读取
            model (str, optional): 模型接入点ID，如果未提供则从环境变量DOUBAO_MODEL读取
        """
        # 从环境变量获取API密钥
        if api_key is None:
            api_key = os.getenv('DOUBAO_API_KEY')
            if not api_key:
                raise ValueError(
                    "API密钥未提供。请设置环境变量 DOUBAO_API_KEY 或传入 api_key 参数。\n"
                    "设置方法：\n"
                    "  Linux/Mac: export DOUBAO_API_KEY='your-api-key'\n"
                    "  Windows: set DOUBAO_API_KEY=your-api-key"
                )
        
        # 从环境变量获取模型ID
        if model is None:
            model = os.getenv('DOUBAO_MODEL')
            if not model:
                raise ValueError(
                    "模型ID未提供。请设置环境变量 DOUBAO_MODEL 或传入 model 参数。\n"
                    "设置方法：\n"
                    "  Linux/Mac: export DOUBAO_MODEL='your-model-endpoint'\n"
                    "  Windows: set DOUBAO_MODEL=your-model-endpoint"
                )
        
        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key,
        )
        self.model = model
    
    def chat(self, message: str, system_prompt: str = None, verbose: bool = True) -> str:
        """
        与 AI 模型对话
        
        Args:
            message (str): 用户消息
            system_prompt (str): 系统提示词
            verbose (bool): 是否打印详细信息
            
        Returns:
            str: 模型回复，失败时返回 None
        """
        try:
            if verbose:
                print(f"正在调用豆包1.6模型...")
                print(f"用户问题: {message[:50]}...")
                print("-" * 50)
            
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": message
            })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                timeout=60,  # 设置60秒超时
            )
            
            reply = response.choices[0].message.content
            
            if verbose:
                print("模型回复:")
                print("调用成功！")
            
            return reply
            
        except Exception as e:
            error_msg = f"调用失败: {str(e)}"
            if verbose:
                print(error_msg)
            return None


# 为了向后兼容，保留原名称
DoubaoClient = DoubaoClient


def test_ai_client():
    """
    测试 AI 客户端调用
    """
    client = DoubaoClient()
    response = client.chat("你是什么模型？")
    return response


if __name__ == "__main__":
    test_ai_client()
