#!/usr/bin/env python3
"""
自动提交log目录中的分析结果文件到git
检查/log/目录中的*-analysis*文件是否有更新，如果有则提交到git

使用方法:
  python auto_commit_logs.py           # 交互模式（需要确认）
  python auto_commit_logs.py --silent  # 静默模式（适合cron job）
  python auto_commit_logs.py -q        # 静默模式（无输出）
"""

import os
import subprocess
import sys
from datetime import datetime
import glob
import argparse

def run_command(command, check=True):
    """运行shell命令并返回结果"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=check
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip() if e.stdout else "", e.stderr.strip() if e.stderr else "", e.returncode

def check_git_status(verbose=True):
    """检查git状态"""
    log_message("🔍 检查git状态...", verbose)
    
    # 检查是否在git仓库中
    stdout, stderr, returncode = run_command("git rev-parse --git-dir", check=False)
    if returncode != 0:
        log_message("❌ 当前目录不是git仓库", verbose)
        return False
    
    log_message("✅ 当前目录是git仓库", verbose)
    return True

def get_analysis_files(verbose=True):
    """获取log目录中的所有分析文件"""
    log_dir = "log"
    if not os.path.exists(log_dir):
        log_message(f"❌ {log_dir} 目录不存在", verbose)
        return []
    
    # 查找所有的分析文件
    analysis_patterns = [
        "log/*-analysis.md",
        "log/*-analysis-top*.md"
    ]
    
    analysis_files = []
    for pattern in analysis_patterns:
        files = glob.glob(pattern)
        analysis_files.extend(files)
    
    # 标准化路径格式并去重排序
    analysis_files = [f.replace('\\', '/') for f in analysis_files]
    analysis_files = sorted(list(set(analysis_files)))
    
    log_message(f"📄 发现 {len(analysis_files)} 个分析文件", verbose)
    if verbose:
        for file in analysis_files:
            print(f"   - {file}")
    
    return analysis_files

def check_untracked_or_modified_files(analysis_files, verbose=True):
    """检查哪些分析文件是未追踪或已修改的"""
    if not analysis_files:
        return []
    
    log_message("🔍 检查文件状态...", verbose)
    
    # 获取git状态
    stdout, stderr, returncode = run_command("git status --porcelain")
    if returncode != 0:
        log_message(f"❌ 获取git状态失败: {stderr}", verbose)
        return []
    
    # 解析git状态输出
    modified_files = []
    untracked_files = []
    
    for line in stdout.split('\n'):
        if not line.strip():
            continue
            
        status = line[:2]
        filename = line[3:].strip()
        
        # 只关心分析文件
        if filename in analysis_files:
            if status.strip() == '??':  # 未追踪
                untracked_files.append(filename)
                log_message(f"   📝 未追踪: {filename}", verbose)
            elif 'M' in status or 'A' in status:  # 修改或新增
                modified_files.append(filename)
                log_message(f"   📝 已修改: {filename}", verbose)
    
    all_changed_files = untracked_files + modified_files
    
    if all_changed_files:
        log_message(f"✅ 发现 {len(all_changed_files)} 个需要提交的分析文件", verbose)
    else:
        log_message("ℹ️  没有需要提交的分析文件", verbose)
    
    return all_changed_files

def commit_and_push_files(files_to_commit, verbose=True):
    """提交并推送文件到git"""
    if not files_to_commit:
        log_message("ℹ️  没有文件需要提交", verbose)
        return True
    
    log_message(f"📤 准备提交 {len(files_to_commit)} 个文件...", verbose)
    
    # 生成当前时间戳
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Log: Auto Update {current_time}"
    
    try:
        # 添加文件到暂存区
        log_message("📋 添加文件到暂存区...", verbose)
        for file in files_to_commit:
            stdout, stderr, returncode = run_command(f'git add "{file}"')
            if returncode != 0:
                log_message(f"❌ 添加文件失败 {file}: {stderr}", verbose)
                return False
            if verbose:
                print(f"   ✅ 已添加: {file}")
        
        # 提交
        log_message("💾 提交更改...", verbose)
        stdout, stderr, returncode = run_command(f'git commit -m "{commit_message}"')
        if returncode != 0:
            log_message(f"❌ 提交失败: {stderr}", verbose)
            return False
        
        log_message(f"✅ 提交成功: {commit_message}", verbose)
        if verbose:
            print(f"📝 提交详情:\n{stdout}")
        
        # 推送到远程仓库
        log_message("🚀 推送到远程仓库...", verbose)
        stdout, stderr, returncode = run_command("git push origin main")
        if returncode != 0:
            # 如果main分支推送失败，尝试master分支
            log_message("⚠️  推送到main分支失败，尝试master分支...", verbose)
            stdout, stderr, returncode = run_command("git push origin master")
            if returncode != 0:
                log_message(f"❌ 推送失败: {stderr}", verbose)
                return False
        
        log_message("✅ 推送成功!", verbose)
        if verbose:
            print(f"📤 推送详情:\n{stdout}")
        
        return True
        
    except Exception as e:
        log_message(f"❌ 提交过程出错: {e}", verbose)
        return False

def log_message(message, verbose=True):
    """输出日志信息"""
    if verbose:
        print(message)

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='自动提交log分析结果文件到git')
    parser.add_argument('--silent', '-s', action='store_true', help='静默模式（自动提交，适合cron job）')
    parser.add_argument('--quiet', '-q', action='store_true', help='安静模式（无输出）')
    args = parser.parse_args()
    
    # 确定运行模式
    silent_mode = args.silent or args.quiet
    verbose = not args.quiet
    
    log_message("🤖 自动提交log分析结果脚本", verbose)
    if not args.quiet:
        log_message("=" * 50, verbose)
    
    # 检查git状态
    if not check_git_status(verbose):
        sys.exit(1)
    
    # 获取分析文件
    analysis_files = get_analysis_files(verbose)
    if not analysis_files:
        log_message("ℹ️  没有找到分析文件", verbose)
        sys.exit(0)
    
    # 检查哪些文件需要提交
    files_to_commit = check_untracked_or_modified_files(analysis_files, verbose)
    if not files_to_commit:
        log_message("✅ 所有分析文件都已是最新状态", verbose)
        sys.exit(0)
    
    # 显示将要提交的文件
    if verbose and not silent_mode:
        print("\n📋 将要提交的文件:")
        for file in files_to_commit:
            print(f"   - {file}")
    
    # 交互模式需要确认，静默模式直接提交
    if not silent_mode:
        try:
            confirm = input("\n❓ 是否继续提交这些文件? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ 用户取消操作")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\n❌ 用户中断操作")
            sys.exit(0)
    
    # 提交并推送
    success = commit_and_push_files(files_to_commit, verbose)
    
    if success:
        log_message(f"🎉 自动提交完成! 已提交 {len(files_to_commit)} 个文件", verbose)
        log_message(f"📊 提交时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", verbose)
    else:
        log_message("💥 自动提交失败!", verbose)
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ 脚本被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 脚本执行出错: {e}")
        sys.exit(1)