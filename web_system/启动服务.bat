@echo off
chcp 65001 >nul
echo ========================================
echo   未来社区建设方案生成系统
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python 环境，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [完成] Python 环境正常

echo.
echo [2/3] 安装依赖包...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [警告] 依赖包安装可能有问题，但不影响继续运行
)
echo [完成] 依赖包安装完成

echo.
echo [3/3] 创建必要目录...
if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs
if not exist "templates" mkdir templates
echo [完成] 目录创建完成

echo.
echo ========================================
echo   启动服务...
echo ========================================
echo.
echo 访问地址：http://localhost:5000
echo.
echo 按 Ctrl+C 停止服务
echo.

python app.py

pause
