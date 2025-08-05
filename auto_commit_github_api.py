#!/usr/bin/env python3
"""
GitHub API 自动提交脚本
用于解决 render 服务重启导致日志丢失的问题
通过 GitHub API 直接提交文件到仓库
"""

import os
import base64
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, Dict, Any


class GitHubAutoCommit:
    """GitHub API 自动提交工具类"""
    
    def __init__(self):
        """初始化 GitHub API 客户端"""
        load_dotenv()
        
        self.token = os.getenv('GITHUB_TOKEN')
        self.repo = os.getenv('GITHUB_REPO')
        self.branch = os.getenv('GITHUB_BRANCH', 'main')
        
        if not self.token:
            raise ValueError("GITHUB_TOKEN not found in environment variables")
        if not self.repo:
            raise ValueError("GITHUB_REPO not found in environment variables")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "auto-commit-script"
        }
        
        # Git 提交信息配置
        self.git_name = "auto-commit"
        self.git_email = "no-reply@autocommit.com"
    
    def get_file_sha(self, file_path: str) -> Optional[str]:
        """
        获取文件的 SHA 值（如果文件存在）
        
        Args:
            file_path: 文件在仓库中的路径
            
        Returns:
            文件的 SHA 值，如果文件不存在则返回 None
        """
        url = f"{self.base_url}/repos/{self.repo}/contents/{file_path}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get('sha')
            elif response.status_code == 404:
                # 文件不存在
                return None
            else:
                print(f"获取文件 SHA 失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"获取文件 SHA 时出错: {e}")
            return None
    
    def read_local_file(self, local_path: str) -> str:
        """
        读取本地文件内容
        
        Args:
            local_path: 本地文件路径
            
        Returns:
            文件内容的 base64 编码
        """
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 将内容编码为 base64
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('utf-8')
            return content_base64
        except Exception as e:
            raise Exception(f"读取本地文件失败: {e}")
    
    def commit_file(self, local_path: str, repo_path: str, commit_message: str = None) -> Dict[str, Any]:
        """
        提交文件到 GitHub 仓库
        
        Args:
            local_path: 本地文件路径
            repo_path: 仓库中的文件路径
            commit_message: 提交信息（可选）
            
        Returns:
            提交结果信息
        """
        # 检查本地文件是否存在
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"本地文件不存在: {local_path}")
        
        # 读取文件内容
        content_base64 = self.read_local_file(local_path)
        
        # 获取现有文件的 SHA（如果存在）
        file_sha = self.get_file_sha(repo_path)
        
        # 生成提交信息
        if not commit_message:
            file_name = os.path.basename(repo_path)
            commit_message = f"Log: Auto Commit {file_name}"
        
        # 构建请求数据
        data = {
            "message": commit_message,
            "content": content_base64,
            "branch": self.branch,
            "committer": {
                "name": self.git_name,
                "email": self.git_email
            },
            "author": {
                "name": self.git_name,
                "email": self.git_email
            }
        }
        
        # 如果文件已存在，需要提供 SHA
        if file_sha:
            data["sha"] = file_sha
            action = "更新"
        else:
            action = "创建"
        
        # 发送请求
        url = f"{self.base_url}/repos/{self.repo}/contents/{repo_path}"
        
        try:
            response = requests.put(url, headers=self.headers, data=json.dumps(data))
            
            if response.status_code in [200, 201]:
                result_data = response.json()
                print(f"✅ 成功{action}文件: {repo_path}")
                print(f"📝 提交信息: {commit_message}")
                print(f"🔗 提交链接: {result_data['commit']['html_url']}")
                
                return {
                    "success": True,
                    "action": action,
                    "file_path": repo_path,
                    "commit_message": commit_message,
                    "commit_url": result_data['commit']['html_url'],
                    "sha": result_data['content']['sha']
                }
            else:
                error_msg = f"提交失败: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code
                }
        
        except Exception as e:
            error_msg = f"提交时出错: {e}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def commit_file_by_name(self, file_name: str, folder: str = "log") -> Dict[str, Any]:
        """
        根据文件名提交 log 目录下的文件
        
        Args:
            file_name: 文件名
            folder: 文件所在的文件夹（默认为 "log"）
            
        Returns:
            提交结果信息
        """
        local_path = os.path.join(folder, file_name)
        repo_path = f"{folder}/{file_name}"
        
        return self.commit_file(local_path, repo_path)


def main():
    """主函数 - 命令行接口"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python auto_commit_github_api.py <file_name>")
        print("示例: python auto_commit_github_api.py 2025-07-25-cs.CV-analysis-top5.md")
        sys.exit(1)
    
    file_name = sys.argv[1]
    
    try:
        committer = GitHubAutoCommit()
        result = committer.commit_file_by_name(file_name)
        
        if result["success"]:
            print(f"\n🎉 文件 {file_name} 提交成功！")
        else:
            print(f"\n💥 文件 {file_name} 提交失败: {result.get('error', '未知错误')}")
            sys.exit(1)
    
    except Exception as e:
        print(f"💥 程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
