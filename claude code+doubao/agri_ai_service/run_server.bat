@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  农业AI服务 - 启动脚本
echo ========================================
echo.
echo 提示：直接关闭本窗口即可停止服务器
echo.
echo 正在启动服务器（main.py 会自动清理旧端口进程）...
echo.

python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

echo.
echo 服务器已停止。
pause >nul
