#!/bin/bash
# 自动提交log目录中的分析结果文件到git

echo "🤖 自动提交log分析结果脚本"
echo "=================================================="

# 检查是否在git仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ 当前目录不是git仓库"
    exit 1
fi

echo "✅ 当前目录是git仓库"

# 检查log目录是否存在
if [ ! -d "log" ]; then
    echo "❌ log目录不存在"
    exit 1
fi

echo "📂 检查log目录中的分析文件..."

# 查找所有分析文件
analysis_files=$(find log -name "*-analysis*.md" 2>/dev/null || true)

if [ -z "$analysis_files" ]; then
    echo "ℹ️  没有找到分析文件"
    exit 0
fi

echo "📄 发现的分析文件:"
echo "$analysis_files" | sed 's/^/   - /'

# 检查git状态，查找未追踪或已修改的分析文件
echo "🔍 检查文件状态..."

# 获取有变化的分析文件
changed_files=""
while IFS= read -r file; do
    if [ -f "$file" ]; then
        # 检查文件是否在git中被追踪且有变化，或者未被追踪
        if git ls-files --error-unmatch "$file" > /dev/null 2>&1; then
            # 文件被追踪，检查是否有修改
            if ! git diff --quiet "$file" 2>/dev/null; then
                changed_files="$changed_files$file\n"
                echo "   📝 已修改: $file"
            fi
        else
            # 文件未被追踪
            changed_files="$changed_files$file\n"
            echo "   📝 未追踪: $file"
        fi
    fi
done <<< "$analysis_files"

# 移除最后的换行符
changed_files=$(echo -e "$changed_files" | sed '/^$/d')

if [ -z "$changed_files" ]; then
    echo "✅ 所有分析文件都已是最新状态"
    exit 0
fi

echo "📋 需要提交的文件:"
echo "$changed_files" | sed 's/^/   - /'

# 生成提交信息
current_time=$(date "+%Y-%m-%d %H:%M:%S")
commit_message="Log: Auto Update $current_time"

echo "💾 准备提交..."

# 添加文件到暂存区
while IFS= read -r file; do
    if [ -n "$file" ]; then
        git add "$file"
        echo "   ✅ 已添加: $file"
    fi
done <<< "$changed_files"

# 提交
echo "📤 执行提交..."
if git commit -m "$commit_message"; then
    echo "✅ 提交成功: $commit_message"
    
    # 推送到远程仓库
    echo "🚀 推送到远程仓库..."
    if git push origin main 2>/dev/null; then
        echo "✅ 推送到main分支成功!"
    elif git push origin master 2>/dev/null; then
        echo "✅ 推送到master分支成功!"
    else
        echo "❌ 推送失败，请检查远程仓库配置"
        exit 1
    fi
    
    echo "🎉 自动提交完成!"
else
    echo "❌ 提交失败"
    exit 1
fi