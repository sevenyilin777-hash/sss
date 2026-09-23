#!/bin/bash
# 双击启动: 本地服务器 + 自动打开浏览器 (摄像头手部交互需要 http 环境)
cd "$(dirname "$0")"
PORT=8940
echo "🛸 Alien Tunnel 梦境隧道已启动"
echo "   地址: http://localhost:$PORT  (关闭本窗口即停止服务)"
open "http://localhost:$PORT/index.html"
python3 -m http.server $PORT
