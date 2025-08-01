#!/usr/bin/env python3
"""
测试GitHub Actions备份API功能
"""

import os
import hmac
import hashlib
import requests
import json

def test_backup_api():
    """测试备份API"""
    print("🧪 测试GitHub Actions备份API")
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
        "User-Agent": "Test-Backup-Script/1.0"
    }
    
    # 测试本地API (假设server.py在运行)
    local_url = "http://localhost:8080/internal/backup"
    
    print(f"📡 测试本地API: {local_url}")
    
    try:
        # 先设置测试环境变量
        os.environ["BACKUP_SECRET"] = test_secret
        
        response = requests.post(local_url, headers=headers, timeout=30)
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API测试成功!")
            result = response.json()
            print("📄 响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif response.status_code == 403:
            print("❌ 签名验证失败")
            print("💡 可能原因: BACKUP_SECRET配置不正确")
        else:
            print(f"❌ API测试失败: {response.status_code}")
            print(f"📄 错误内容: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到本地服务器")
        print("💡 请确保server.py正在运行: python server.py")
    except Exception as e:
        print(f"❌ 测试异常: {e}")

def test_signature_generation():
    """测试签名生成"""
    print("\n🔐 测试签名生成")
    print("-" * 30)
    
    secret = "test-secret-123"
    message = "run"
    
    # Python方式
    python_sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    print(f"Python签名: {python_sig}")
    
    # 模拟openssl命令的结果格式说明
    print("对应的openssl命令:")
    print(f'echo -n "{message}" | openssl dgst -sha256 -hmac "{secret}" | cut -d\' \' -f2')

if __name__ == "__main__":
    test_signature_generation()
    test_backup_api()