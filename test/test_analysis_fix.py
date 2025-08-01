#!/usr/bin/env python3
"""
测试分析功能修复的脚本
"""

import requests
import time
import json
import sys
import os

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def test_analysis_functionality():
    """测试分析功能是否正常工作"""
    
    print("🧪 测试分析功能修复...")
    print("=" * 50)
    
    base_url = "http://localhost:8080"
    test_date = "2025-07-31"
    test_category = "cs.AI"
    
    # 检查服务器是否运行
    try:
        response = requests.get(base_url, timeout=5)
        print("✅ 服务器运行正常")
    except requests.exceptions.RequestException:
        print("❌ 服务器未运行，请先启动: python server.py")
        return False
    
    # 测试1：检查环境变量配置
    print(f"\n📝 测试1: 检查豆包API配置...")
    
    if not os.getenv('DOUBAO_API_KEY'):
        print("❌ 环境变量 DOUBAO_API_KEY 未设置")
        print("🔧 请按照README.md配置环境变量或创建.env文件")
        return False
    
    print("✅ 豆包API密钥已配置")
    
    # 测试2：启动小规模分析
    print(f"\n🤖 测试2: 启动分析任务（{test_category} 前2篇论文）...")
    
    try:
        # 启动分析
        analyze_response = requests.post(
            f"{base_url}/api/analyze_papers",
            headers={"Content-Type": "application/json"},
            json={"date": test_date, "category": test_category, "test_count": 2},
            timeout=10
        )
        
        if analyze_response.status_code != 200:
            print(f"❌ 启动分析失败: {analyze_response.status_code}")
            print(f"错误信息: {analyze_response.text}")
            return False
        
        task_data = analyze_response.json()
        task_id = task_data.get('task_id')
        print(f"✅ 分析任务启动成功: {task_id}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 分析请求失败: {e}")
        return False
    
    # 测试3：监控分析进度
    print(f"\n📊 测试3: 监控分析进度...")
    
    try:
        # 监控进度
        progress_url = f"{base_url}/api/analysis_progress?date={test_date}&category={test_category}"
        
        print("🔍 开始监控进度...")
        start_time = time.time()
        max_wait_time = 120  # 最多等待2分钟
        
        with requests.get(progress_url, stream=True, timeout=max_wait_time) as response:
            if response.status_code != 200:
                print(f"❌ 进度监控失败: {response.status_code}")
                return False
            
            completed = False
            error_occurred = False
            progress_count = 0
            
            for line in response.iter_lines(decode_unicode=True):
                if time.time() - start_time > max_wait_time:
                    print("⏰ 超时，停止监控")
                    break
                
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])  # 移除 'data: ' 前缀
                        status = data.get('status', '')
                        current = data.get('current', 0)
                        total = data.get('total', 0)
                        
                        if current > 0:
                            progress_count += 1
                            print(f"   📄 进度: {current}/{total} ({status})")
                        
                        if status == 'error':
                            error_occurred = True
                            error_msg = data.get('error', '未知错误')
                            print(f"❌ 分析出错: {error_msg}")
                            break
                            
                    except json.JSONDecodeError:
                        continue
                
                elif line.startswith('event: complete'):
                    completed = True
                    print("✅ 分析完成！")
                    break
                
                elif line.startswith('event: error'):
                    error_occurred = True
                    print("❌ 分析过程出错")
                    break
            
            if error_occurred:
                return False
            elif completed:
                print(f"🎉 分析成功完成，共监控到 {progress_count} 个进度更新")
                return True
            else:
                print("⚠️  分析状态不明确")
                return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ 进度监控失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 分析功能修复验证工具")
    print("这个工具将验证豆包API配置和分析功能是否正常")
    
    # 检查依赖
    try:
        import requests
    except ImportError:
        print("❌ 缺少requests依赖，请运行: pip install requests")
        return False
    
    # 运行测试
    success = test_analysis_functionality()
    
    if success:
        print("\n🎊 所有测试通过！分析功能已修复")
        print("💡 现在您可以在Web界面中正常使用AI分析功能")
        return True
    else:
        print("\n💥 测试失败，请检查配置和日志")
        print("🔧 建议检查:")
        print("  1. 豆包API密钥是否正确设置")
        print("  2. 服务器终端是否有错误信息")
        print("  3. 网络连接是否正常")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 测试过程出错: {e}")
        sys.exit(1)