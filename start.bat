@echo off
echo ========================================
echo    Arxiv文章初筛小助手
echo ========================================
echo.
echo 正在启动服务器...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查依赖是否安装
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误: 依赖安装失败
        pause
        exit /b 1
    )
)

echo 启动服务器...
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止服务器
echo.

python server.py

pause 