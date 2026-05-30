#!/bin/bash
# 农业AI服务 - 启动脚本 (Bash版)
# 自动清理旧进程后启动

cd "$(dirname "$0")"

echo "正在关闭端口 8000 上的旧进程..."
# Windows 下通过 netstat + taskkill 清理
OLD_PID=$(netstat -aon | grep ":8000" | grep "LISTENING" | awk '{print $NF}' | head -1)
if [ -n "$OLD_PID" ]; then
    taskkill //F //PID "$OLD_PID" 2>/dev/null
    echo "已关闭进程 $OLD_PID"
fi

echo "正在启动服务器..."
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
