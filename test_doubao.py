import os
from openai import OpenAI

def test_doubao_model():
    """
    测试doubao1.6模型调用
    """
    try:
        # 初始化Ark客户端
        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key="53a1f946-1d52-44e1-aecf-cdea96c58e97",  # 你的API Key
        )
        
        print("正在调用doubao1.6模型...")
        print("用户问题: 你是什么模型？")
        print("-" * 50)
        
        # 调用模型
        response = client.chat.completions.create(
            model="ep-20250730235134-2q9zk",  # 你的接入点ID
            messages=[
                {
                    "role": "user",
                    "content": "你是什么模型？"
                }
            ],
        )
        
        print("模型回复:")
        print(response.choices[0].message.content)
        print("-" * 50)
        print("调用成功！")
        
    except Exception as e:
        print(f"调用失败: {str(e)}")

if __name__ == "__main__":
    test_doubao_model() 