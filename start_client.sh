#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "🦊 [INFO] 启动 PZ 创意工坊客户端提取器..."

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] 未检测到 python3，请先安装 Python 3.8+。"
    exit 1
fi

if ! python3 -c "import requests" &>/dev/null; then
    echo "[WARN] 正在安装必要依赖..."
    pip3 install -r requirements.txt || pip install -r requirements.txt
fi

python3 client_extractor.py
