# 自动提交Log分析结果脚本使用说明

## 📋 脚本说明

本项目提供两个脚本用于自动提交`log/`目录中的分析结果文件：

1. **`auto_commit_logs.py`** - 主脚本（推荐）
2. **`auto_commit_logs.sh`** - Shell脚本（备用）

## 🚀 使用方法

### Python脚本（推荐）

```bash
# 交互模式（需要确认）
python auto_commit_logs.py

# 静默模式（自动提交，适合cron job）
python auto_commit_logs.py --silent

# 安静模式（无输出，适合后台运行）
python auto_commit_logs.py --quiet
```

### Shell脚本（备用）

```bash
# 直接运行（自动提交）
./auto_commit_logs.sh
```

## 📝 功能特点

- 自动检测`log/*-analysis*.md`文件的变化
- 支持交互模式和静默模式
- 自动生成格式化的提交信息：`Log: Auto Update YYYY-MM-DD HH:MM:SS`
- 支持推送到`main`或`master`分支
- 完整的错误处理和状态报告

## 🔄 自动化部署

### Cron Job (Linux/Mac/Render)

```bash
# 每小时检查一次（静默模式）
0 * * * * cd /path/to/arxiv-accelerator && python auto_commit_logs.py --quiet

# 每天凌晨2点检查（普通模式）
0 2 * * * cd /path/to/arxiv-accelerator && python auto_commit_logs.py --silent
```

### 本地定时任务

```bash
# Windows任务计划程序
# 创建基本任务，设置操作为：
# 程序：python
# 参数：auto_commit_logs.py --silent
# 起始位置：项目目录
```

## ⚠️ 注意事项

1. **必须在git仓库中运行**
2. **必须有远程仓库推送权限**
3. **确保Python环境可用**（Render服务器支持）
4. **路径格式自动处理**（支持Windows/Linux）

## 📊 返回码

- `0` - 成功（操作完成或无需操作）
- `1` - 失败（错误或权限问题）

这样设计可以确保在本地开发和Render服务器上都能正常工作。