#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] 未检测到 python3，请先安装 Python 3.8+。"
    exit 1
fi

if [ $# -eq 0 ]; then
    echo "========================================================"
    echo "  🧟 PZ-Server-ModManager - 服务端注入与下载调度器"
    echo "========================================================"
    echo "用法示例:"
    echo "  ./start_server.sh -i ~/Zomboid/Server/myserver.ini"
    echo "  ./start_server.sh -i ~/Zomboid/Server/myserver.ini -d"
    echo "========================================================"
    python3 server_deployer.py --help
    echo ""
    read -rp "请输入服务器 .ini 路径: " ini_path
    if [ -n "$ini_path" ]; then
        python3 server_deployer.py -i "$ini_path"
    fi
else
    python3 server_deployer.py "$@"
fi
