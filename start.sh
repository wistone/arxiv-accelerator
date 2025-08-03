#!/bin/bash

# Arxiv智能分析助手 - 启动脚本
# 支持双前端：React (现代) + HTML (经典)

# 默认配置
BUILD_ONLY=false
SKIP_FRONTEND=false
FRONTEND_MODE="auto"  # auto, react, html

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --frontend)
            FRONTEND_MODE="$2"
            shift 2
            ;;
        --help)
            echo "Arxiv智能分析助手 - 启动脚本"
            echo ""
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --build-only     仅构建，不启动服务器 (用于Render部署)"
            echo "  --skip-frontend  跳过前端构建，仅启动后端"
            echo "  --frontend MODE  指定前端模式: auto|react|html"
            echo "  --help          显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                    # 自动检测并启动最佳前端"
            echo "  $0 --frontend react  # 强制使用React前端"
            echo "  $0 --frontend html   # 强制使用HTML前端"
            echo "  $0 --skip-frontend   # 仅启动后端"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "    Arxiv智能分析助手"
echo "    双前端支持版本"
echo "========================================"
echo

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python3"
    exit 1
fi

echo "✅ Python环境检查通过"

# 安装Python依赖
if ! python3 -c "import flask" &> /dev/null; then
    echo "📦 正在安装Python依赖..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 错误: Python依赖安装失败"
        exit 1
    fi
else
    echo "✅ Python依赖检查通过"
fi

# 前端处理
if [ "$SKIP_FRONTEND" = false ]; then
    # 检查Node.js环境 (如果有frontend目录)
    if [ -d "frontend" ]; then
        if command -v node &> /dev/null && command -v npm &> /dev/null; then
            echo "✅ Node.js环境检查通过"
            
            # 进入frontend目录安装依赖
            cd frontend
            
            if [ ! -d "node_modules" ]; then
                echo "📦 正在安装前端依赖..."
                npm install
                if [ $? -ne 0 ]; then
                    echo "⚠️  警告: 前端依赖安装失败，将使用HTML界面"
                    FRONTEND_MODE="html"
                fi
            else
                echo "✅ 前端依赖检查通过"
            fi
            
            # 构建React前端
            if [ "$FRONTEND_MODE" != "html" ]; then
                echo "🔨 正在构建React前端..."
                npm run build
                if [ $? -eq 0 ]; then
                    echo "✅ React前端构建成功"
                    FRONTEND_MODE="react"
                else
                    echo "⚠️  警告: React前端构建失败，将使用HTML界面"
                    FRONTEND_MODE="html"
                fi
            fi
            
            cd ..
        else
            echo "⚠️  Node.js未安装，将使用经典HTML界面"
            FRONTEND_MODE="html"
        fi
    else
        echo "📄 未发现frontend目录，使用经典HTML界面"
        FRONTEND_MODE="html"
    fi
else
    echo "⏭️  跳过前端构建"
fi

# 如果是仅构建模式，则退出
if [ "$BUILD_ONLY" = true ]; then
    echo "✅ 构建完成！"
    exit 0
fi

# 启动服务器
echo ""
echo "🚀 启动服务器..."

if [ "$FRONTEND_MODE" = "react" ]; then
    echo "🎨 前端界面: React (现代界面)"
    echo "📱 访问地址: http://localhost:8080"
    echo "📄 经典界面: http://localhost:8080/classic"
elif [ "$FRONTEND_MODE" = "html" ]; then
    echo "📄 前端界面: HTML (经典界面)"
    echo "📱 访问地址: http://localhost:8080"
else
    echo "🔄 前端界面: 自动检测"
    echo "📱 访问地址: http://localhost:8080"
fi

echo "⏹️  按 Ctrl+C 停止服务器"
echo ""

# 设置环境变量供server.py使用
export FRONTEND_MODE="$FRONTEND_MODE"

python3 server.py 