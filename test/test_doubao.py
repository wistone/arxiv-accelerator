import os
import sys

# 添加父目录到Python路径以导入doubao_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv未安装，使用系统环境变量")

from doubao_client import DoubaoClient

def test_doubao_model():
    """
    测试doubao1.6模型调用
    """
    try:
        print("🧪 开始测试豆包API连接...")
        print("📝 检查环境变量配置...")
        
        # 检查环境变量
        api_key = os.getenv('DOUBAO_API_KEY')
        model = os.getenv('DOUBAO_MODEL')
        
        if not api_key:
            print("❌ 环境变量 DOUBAO_API_KEY 未设置")
            print("🔧 请设置环境变量或创建.env文件")
            print("   Linux/Mac: export DOUBAO_API_KEY='your-api-key'")
            print("   Windows: set DOUBAO_API_KEY=your-api-key")
            return False
        
        print(f"✅ API密钥: {api_key[:10]}...{api_key[-4:]}")
        print(f"✅ 模型ID: {model if model else '使用默认模型'}")
        
        # 初始化客户端
        client = DoubaoClient()
        
        print("\n🤖 测试模型调用...")
        response = client.chat("你是什么模型？请简要介绍一下自己。")
        
        if response:
            print("✅ 豆包API连接成功！")
            return True
        else:
            print("❌ 豆包API调用失败")
            return False
        
    except ValueError as e:
        print(f"❌ 配置错误: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 调用失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_doubao_model()
    if success:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n💥 测试失败，请检查配置")
        sys.exit(1) 