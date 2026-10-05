@echo off
chcp 65001 >nul
title PZ ModManager - Client Extractor
cd /d "%~dp0"

echo [INFO] 正在启动 PZ 创意工坊客户端提取器...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未检测到 Python 环境，请先安装 Python 3.8+ 并添加至 PATH。
    pause
    exit /b 1
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [WARN] 检测到依赖缺失，尝试自动安装...
    pip install -r requirements.txt
)

python client_extractor.py
if errorlevel 1 (
    echo [ERROR] 程序异常退出。
    pause
)
