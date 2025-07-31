#!/bin/bash

echo "========================================"
echo "    Arxiv文章初筛小助手"
echo "========================================"
echo

echo "正在启动服务器..."
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖是否安装
if ! python3 -c "import flask" &> /dev/null; then
    echo "正在安装依赖包..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败"
        exit 1
    fi
fi

echo "启动服务器..."
echo "访问地址: http://localhost:8080"
echo "按 Ctrl+C 停止服务器"
echo

python3 server.py 