#!/bin/zsh
set -euo pipefail

ROOT_DIR="/Users/shijianping/FunnyStaff/arxiv-accelerator"
LOG_DIR="$ROOT_DIR/log"
PROMPT_ID="d3094bb1-486e-4297-a274-43be3deea1c1"

# 加载环境变量（如果存在）
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

echo "开始批量导入分析结果到数据库"
echo "ROOT_DIR=$ROOT_DIR"
echo "PROMPT_ID=$PROMPT_ID"

count_total=0
count_ok=0
count_skip=0
count_missing=0
count_err=0

# 按文件名排序遍历，排除 *-fail.md
files=($(find "$LOG_DIR" -type f -name "*-analysis*.md" ! -name "*-fail.md" | sort))

echo "匹配文件数: ${#files[@]}"
if [ ${#files[@]} -gt 0 ]; then
  echo "示例前5个:"
  printf '%s\n' "${files[@]:0:5}"
fi

if [ ${#files[@]} -eq 0 ]; then
  echo "未找到需要导入的 -analysis*.md 文件"
  exit 0
fi

for f in "${files[@]}"; do
  count_total=$((count_total+1))
  echo "\n================================================================================"
  echo "[${count_total}] 导入文件: $f"
  echo "================================================================================"
  tmpfile=$(mktemp)
  # 实时输出，同时保存到临时文件以便解析 SUMMARY
  if python3 "$ROOT_DIR/import_analysis_to_db.py" "$f" --prompt-id "$PROMPT_ID" 2>&1 | tee "$tmpfile"; then
    :
  else
    echo "导入命令返回非零，但继续统计：$f" >&2
  fi

  summary_line=$(tail -n 1 "$tmpfile" 2>/dev/null || echo "")
  if echo "$summary_line" | grep -q "SUMMARY:"; then
    updated=$(echo "$summary_line" | grep -o '"updated"[[:space:]]*:[[:space:]]*[0-9]\+' | grep -o '[0-9]\+' || true)
    skipped=$(echo "$summary_line" | grep -o '"skipped"[[:space:]]*:[[:space:]]*[0-9]\+' | grep -o '[0-9]\+' || true)
    missing=$(echo "$summary_line" | grep -o '"papers_missing"[[:space:]]*:[[:space:]]*[0-9]\+' | grep -o '[0-9]\+' || true)
    [ -z "$updated" ] && updated=0
    [ -z "$skipped" ] && skipped=0
    [ -z "$missing" ] && missing=0
    count_ok=$((count_ok + updated))
    count_skip=$((count_skip + skipped))
    count_missing=$((count_missing + missing))
  else
    echo "未检测到 SUMMARY，视为失败: $f" >&2
    count_err=$((count_err+1))
  fi
  rm -f "$tmpfile" || true
done

echo "\n===================== 总结 ====================="
echo "文件总数: $count_total"
echo "成功写入(analysis_results.updated 累计): $count_ok"
echo "跳过(已存在): $count_skip"
echo "缺失paper记录: $count_missing"
echo "失败文件数: $count_err"
echo "=============================================="


