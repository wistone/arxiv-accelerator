#!/bin/bash

# =============================================================================
# Arxiv Accelerator - 自动备份日志脚本 (GitHub Actions版)
# =============================================================================
# 用途: 通过GitHub Actions触发，复用auto_commit_logs.py自动提交和推送日志分析文件
# 作者: Arxiv Accelerator Team
# 版本: 1.0.0
# =============================================================================

set -e  # 遇到错误立即退出

echo "🤖 [GitHub Actions] 自动备份日志分析文件"
echo "=================================================="
echo "⏰ 执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "📂 当前目录: $(pwd)"

# 检查必要文件是否存在
if [ ! -f "auto_commit_logs.py" ]; then
    echo "❌ 错误: auto_commit_logs.py 脚本不存在"
    exit 1
fi

echo "✅ 找到 auto_commit_logs.py 脚本"

# 检查Python是否可用
if ! command -v python > /dev/null 2>&1; then
    if ! command -v python3 > /dev/null 2>&1; then
        echo "❌ 错误: Python未安装或不可用"
        exit 1
    else
        PYTHON_CMD="python3"
    fi
else
    PYTHON_CMD="python"
fi

echo "✅ Python可用: $PYTHON_CMD"

# 执行自动提交脚本
echo "🚀 执行自动提交脚本..."
echo "📝 使用安静模式以适配GitHub Actions环境"

# 使用--quiet模式确保输出简洁，适合GitHub Actions
if $PYTHON_CMD auto_commit_logs.py --quiet; then
    echo "🎉 备份操作成功完成!"
    echo "📊 统计信息:"
    echo "   - 提交时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "   - 执行环境: GitHub Actions"
    echo "   - 脚本: auto_commit_logs.py --quiet"
    exit 0
else
    echo "❌ 备份操作失败"
    echo "💡 提示: 可能没有需要提交的文件，或者git操作失败"
    exit 1
fi