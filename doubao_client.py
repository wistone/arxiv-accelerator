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
    Doubao1.6模型调用客户端
    """
    
    def __init__(self, api_key=None, model=None):
        """
        初始化Doubao客户端
        
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
                timeout=60,  # 设置60秒超时
            )
            
            reply = response.choices[0].message.content
            
            if verbose:
                print("模型回复:")
                # print(reply)
                # print("-" * 50)
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