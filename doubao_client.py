import os
from openai import OpenAI

class DoubaoClient:
    """
    Doubao1.6模型调用客户端
    """
    
    def __init__(self, api_key="53a1f946-1d52-44e1-aecf-cdea96c58e97", 
                 model="ep-20250730235134-2q9zk"):
        """
        初始化Doubao客户端
        
        Args:
            api_key (str): API密钥
            model (str): 模型接入点ID
        """
        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key,
        )
        self.model = model
    
    def chat(self, message, system_prompt=None, verbose=True):
        """
        与doubao1.6模型对话
        
        Args:
            message (str): 用户消息
            system_prompt (str): 系统提示词
            verbose (bool): 是否打印详细信息
            
        Returns:
            str: 模型回复
        """
        try:
            if verbose:
                print(f"正在调用doubao1.6模型...")
                if system_prompt:
                    print(f"系统提示词: {system_prompt[:100]}...")
                print(f"用户问题: {message[:100]}...")
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
            )
            
            reply = response.choices[0].message.content
            
            if verbose:
                print("模型回复:")
                print(reply)
                print("-" * 50)
                print("调用成功！")
            
            return reply
            
        except Exception as e:
            error_msg = f"调用失败: {str(e)}"
            if verbose:
                print(error_msg)
            return None

def test_doubao():
    """
    测试doubao1.6模型调用
    """
    client = DoubaoClient()
    response = client.chat("你是什么模型？")
    return response

if __name__ == "__main__":
    test_doubao() 