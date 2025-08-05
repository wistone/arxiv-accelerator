#!/usr/bin/env python3
"""
测试 GitHub API 自动提交功能
测试文件: 2025-07-25-cs.CV-analysis-top5.md
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# 添加父目录到路径，以便导入主模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auto_commit_github_api import GitHubAutoCommit


class TestGitHubAutoCommit(unittest.TestCase):
    """GitHub 自动提交功能测试类"""
    
    def setUp(self):
        """测试前的设置"""
        load_dotenv()
        
        # 检查必需的环境变量
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO')
        
        if not self.github_token or not self.github_repo:
            self.skipTest("缺少必需的环境变量 GITHUB_TOKEN 或 GITHUB_REPO")
    
    def test_init_with_env_vars(self):
        """测试使用环境变量初始化"""
        committer = GitHubAutoCommit()
        
        self.assertIsNotNone(committer.token)
        self.assertIsNotNone(committer.repo)
        self.assertEqual(committer.branch, 'main')
        self.assertEqual(committer.git_name, 'auto-commit-test')
        self.assertEqual(committer.git_email, 'no-reply@autocommit.com')
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_token(self):
        """测试缺少 TOKEN 时的错误处理"""
        with self.assertRaises(ValueError) as context:
            GitHubAutoCommit()
        
        self.assertIn("GITHUB_TOKEN not found", str(context.exception))
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}, clear=True)
    def test_init_without_repo(self):
        """测试缺少 REPO 时的错误处理"""
        with self.assertRaises(ValueError) as context:
            GitHubAutoCommit()
        
        self.assertIn("GITHUB_REPO not found", str(context.exception))
    
    def test_read_local_file(self):
        """测试读取本地文件功能"""
        # 使用存在的测试文件
        test_file_path = "log/2025-07-25-cs.CV-analysis-top5.md"
        
        if not os.path.exists(test_file_path):
            self.skipTest(f"测试文件不存在: {test_file_path}")
        
        committer = GitHubAutoCommit()
        content_base64 = committer.read_local_file(test_file_path)
        
        self.assertIsNotNone(content_base64)
        self.assertIsInstance(content_base64, str)
        
        # 验证是有效的 base64
        import base64
        try:
            decoded = base64.b64decode(content_base64)
            self.assertIsInstance(decoded, bytes)
        except Exception as e:
            self.fail(f"无效的 base64 编码: {e}")
    
    def test_read_nonexistent_file(self):
        """测试读取不存在文件的错误处理"""
        committer = GitHubAutoCommit()
        
        with self.assertRaises(Exception) as context:
            committer.read_local_file("nonexistent_file.txt")
        
        self.assertIn("读取本地文件失败", str(context.exception))
    
    @patch('requests.get')
    def test_get_file_sha_existing(self, mock_get):
        """测试获取已存在文件的 SHA"""
        # 模拟 GitHub API 响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'sha': 'test-sha-value'}
        mock_get.return_value = mock_response
        
        committer = GitHubAutoCommit()
        sha = committer.get_file_sha("test/file.txt")
        
        self.assertEqual(sha, 'test-sha-value')
    
    @patch('requests.get')
    def test_get_file_sha_nonexistent(self, mock_get):
        """测试获取不存在文件的 SHA"""
        # 模拟 404 响应
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        committer = GitHubAutoCommit()
        sha = committer.get_file_sha("nonexistent/file.txt")
        
        self.assertIsNone(sha)


class TestRealCommit(unittest.TestCase):
    """真实提交测试（需要有效的 GitHub 配置）"""
    
    def setUp(self):
        """测试前的设置"""
        load_dotenv()
        
        # 检查必需的环境变量和测试文件
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_repo = os.getenv('GITHUB_REPO')
        self.test_file = "log/2025-07-25-cs.CV-analysis-top5.md"
        
        if not self.github_token or not self.github_repo:
            self.skipTest("缺少必需的环境变量 GITHUB_TOKEN 或 GITHUB_REPO")
        
        if not os.path.exists(self.test_file):
            self.skipTest(f"测试文件不存在: {self.test_file}")
    
    def test_commit_test_file(self):
        """
        测试提交指定的测试文件
        注意: 这是一个真实的提交操作！
        """
        print(f"\n🚀 开始测试提交文件: {self.test_file}")
        
        committer = GitHubAutoCommit()
        result = committer.commit_file_by_name("2025-07-25-cs.CV-analysis-top5.md")
        
        print(f"📋 提交结果: {result}")
        
        # 验证提交结果
        self.assertTrue(result["success"], f"提交失败: {result.get('error', '未知错误')}")
        self.assertIn("file_path", result)
        self.assertIn("commit_message", result)
        self.assertEqual(result["file_path"], "log/2025-07-25-cs.CV-analysis-top5.md")
        
        print(f"✅ 测试通过！文件已成功提交到 GitHub")


def run_test_suite():
    """运行完整的测试套件"""
    print("🧪 开始运行 GitHub API 自动提交测试套件")
    print("=" * 60)
    
    # 运行基础测试
    print("\n📋 运行基础功能测试...")
    suite1 = unittest.TestLoader().loadTestsFromTestCase(TestGitHubAutoCommit)
    runner1 = unittest.TextTestRunner(verbosity=2)
    result1 = runner1.run(suite1)
    
    # 运行真实提交测试（需要用户确认）
    print("\n⚠️  即将运行真实提交测试...")
    print("这将会实际提交文件到 GitHub 仓库！")
    
    user_input = input("是否继续？(y/N): ").strip().lower()
    
    if user_input in ['y', 'yes']:
        print("\n🚀 运行真实提交测试...")
        suite2 = unittest.TestLoader().loadTestsFromTestCase(TestRealCommit)
        runner2 = unittest.TextTestRunner(verbosity=2)
        result2 = runner2.run(suite2)
        
        return result1.wasSuccessful() and result2.wasSuccessful()
    else:
        print("⏭️  跳过真实提交测试")
        return result1.wasSuccessful()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GitHub API 自动提交测试')
    parser.add_argument('--real-commit', action='store_true', 
                        help='直接运行真实提交测试（不询问确认）')
    parser.add_argument('--unit-only', action='store_true',
                        help='只运行单元测试，不进行真实提交')
    
    args = parser.parse_args()
    
    if args.unit_only:
        # 只运行单元测试
        suite = unittest.TestLoader().loadTestsFromTestCase(TestGitHubAutoCommit)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()
    
    elif args.real_commit:
        # 直接运行真实提交测试
        print("🚀 直接运行真实提交测试...")
        
        committer = GitHubAutoCommit()
        result = committer.commit_file_by_name("2025-07-25-cs.CV-analysis-top5.md")
        
        if result["success"]:
            print(f"✅ 测试成功！文件已提交: {result['commit_url']}")
            return True
        else:
            print(f"❌ 测试失败: {result.get('error', '未知错误')}")
            return False
    
    else:
        # 运行完整测试套件
        return run_test_suite()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)