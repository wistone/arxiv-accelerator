#!/usr/bin/env python3
"""
测试新的GitHub Actions备份API功能
验证Render返回文件内容的方案
"""

import os
import hmac
import hashlib
import requests
import json

def test_new_backup_api():
    """测试新的备份API"""
    print("🧪 测试新的GitHub Actions备份API")
    print("=" * 50)
    
    # 使用测试密钥
    test_secret = "f20c02804b8c893cf6abb02ca2f7a0826dba264906cc536de3dac809e918ad47"
    
    # 计算签名
    signature = hmac.new(test_secret.encode(), b"run", hashlib.sha256).hexdigest()
    print(f"🔐 测试签名: {signature}")
    
    # 请求头
    headers = {
        "X-Backup-Sign": signature,
        "Content-Type": "application/json",
        "User-Agent": "Test-New-Backup-Script/1.0"
    }
    
    # 测试本地API
    local_url = "http://localhost:8080/internal/backup"
    
    print(f"📡 测试本地API: {local_url}")
    
    try:
        # 设置测试环境变量
        os.environ["BACKUP_SECRET"] = test_secret
        
        response = requests.post(local_url, headers=headers, timeout=30)
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API测试成功!")
            result = response.json()
            
            # 美化输出
            print("📄 响应内容:")
            print(f"   - 状态: {'成功' if result.get('ok') else '失败'}")
            print(f"   - 消息: {result.get('message', 'N/A')}")
            print(f"   - 文件数量: {result.get('file_count', 0)}")
            print(f"   - 总大小: {result.get('total_size', 0)} 字符")
            print(f"   - 时间戳: {result.get('timestamp', 'N/A')}")
            
            files = result.get('files', {})
            if files:
                print(f"\n📋 文件列表:")
                for filename, file_info in files.items():
                    print(f"   - {filename}")
                    print(f"     路径: {file_info.get('path', 'N/A')}")
                    print(f"     大小: {file_info.get('size', 0)} 字符")
                    print(f"     内容预览: {file_info.get('content', '')[:100]}...")
            
            # 模拟GitHub Actions的文件写入流程
            if files:
                print(f"\n🧪 模拟GitHub Actions文件写入:")
                test_dir = "test_backup_output"
                os.makedirs(test_dir, exist_ok=True)
                
                for filename, file_info in files.items():
                    test_path = os.path.join(test_dir, filename)
                    with open(test_path, 'w', encoding='utf-8') as f:
                        f.write(file_info['content'])
                    print(f"   ✅ 写入测试文件: {test_path}")
                
                print(f"💡 测试文件已写入到 {test_dir}/ 目录")
            
        elif response.status_code == 403:
            print("❌ 签名验证失败")
            print("💡 可能原因: BACKUP_SECRET配置不正确")
        else:
            print(f"❌ API测试失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📄 错误内容: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"📄 错误内容: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到本地服务器")
        print("💡 请确保server.py正在运行: python server.py")
    except Exception as e:
        print(f"❌ 测试异常: {e}")

def cleanup_test_files():
    """清理测试文件"""
    import shutil
    test_dir = "test_backup_output"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"🧹 清理测试目录: {test_dir}")

if __name__ == "__main__":
    try:
        test_new_backup_api()
    finally:
        cleanup_test_files()