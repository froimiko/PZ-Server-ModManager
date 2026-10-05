@echo off
chcp 65001 >nul
title PZ ModManager - Server Deployer
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未检测到 Python 环境，请先安装 Python 3.8+ 并添加至 PATH。
    pause
    exit /b 1
)

if "%~1"=="" (
    echo ========================================================
    echo   🧟 PZ-Server-ModManager - 服务端注入与下载调度器
    echo ========================================================
    echo 用法示例:
    echo   start_server.bat -i "C:\Users\用户名\Zomboid\Server\myserver.ini"
    echo   start_server.bat -i "myserver.ini" -d   (注入并调用 SteamCMD 批量下载)
    echo ========================================================
    python server_deployer.py --help
    echo.
    set /p INI_PATH="请输入服务器 .ini 文件路径 (直接回车退出): "
    if defined INI_PATH (
        python server_deployer.py -i "%INI_PATH%"
    )
    pause
) else (
    python server_deployer.py %*
)
