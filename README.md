<div align="center">

# 🧟 PZ-Server-ModManager
### 僵尸毁灭工程 (Project Zomboid) 双端 Mod 极简同步器与服务端自动化部署

[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=flat-square&logo=python)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-emerald.svg?style=flat-square)](#)
[![License](https://img.shields.io/badge/License-MIT-amber.svg?style=flat-square)](LICENSE)
[![Author](https://img.shields.io/badge/Crafted%20by-Kitsune%20(狐玖)-ff69b4.svg?style=flat-square)](#-关于作者)

<p align="center">
  专为解决《僵尸毁灭工程》联机与自建服务器过程中 <b>Mod 依赖繁琐</b>、<b>配置文件格式反人类</b>、<b>游戏内自动下载无限卡死与循环校验</b> 等痛点而生。<br>
  零侵入、原生 Steam 工坊多盘穿透探测、现代可视化点选、自动配平 <code>Mods</code> 与 <code>WorkshopItems</code>，支持 SteamCMD 极速预热并发拉取。
</p>

[✨ 核心功能](#-核心功能) • [🚀 快速开始](#-快速开始) • [📁 目录结构](#-目录结构) • [🛠️ 进阶用法](#️-进阶配置与调度) • [📝 开源协议](#-开源协议)

---

</div>

## 🌟 核心特性

- **🔍 全盘 Steam 库智能穿透**  
  自动侦测多盘符、自定义盘符及非标准安装路径下的 Steam 游戏库与 Workshop 缓存，秒级提取本地订阅与依赖关系。
- **🖥️ 现代响应式 Web 控制台 (客户端)**  
  无需忍受简陋的终端或丑陋的原生窗口。一键拉起本地管理面板，提供即时过滤搜索、工坊链接直达以及“疑似纯客户端专用（UI/音效/汉化）”智能标记。
- **⚡ 严密的一键对齐导出**  
  输出严谨的 `server_mod_manifest.json`，自动对齐并格式化为 PZ 服务器核心所需的 `Mods=...;` 与 `WorkshopItems=...;` 字符串。
- **🛡️ 零风险防御式注入 (服务端)**  
  支持跨平台（Windows / Linux），写入前自动执行备份（`.bak`），杜绝手动编辑 ini 产生的分号、空格与字段丢失隐患。
- **📦 SteamCMD 并发预载引擎**  
  动态构建下载执行流（RunScript），支持绕过游戏本体直接调度 SteamCMD 进行前置并发下载与完整性校验，彻底告别服务器开服时的卡死轮询。

---

## 🚀 快速开始

无论客户端还是服务端，均提供**开箱即用**的双端快捷启动脚本（Windows `.bat` / Linux `.sh`）。

### 第一步：在客户端（房主 / 玩家机）提取 Mod 清单

1. 双击运行或在终端中执行客户端启动脚本：
   - **Windows**: 双击 `start_client.bat`
   - **Linux / macOS**:
     ```bash
     chmod +x start_client.sh
     ./start_client.sh
     ```
2. 浏览器将自动唤起控制台（默认监听 `http://127.0.0.1:18888`）。
3. 勾选需要部署到服务器的 Mod，点击右上角的 **「💾 导出为服务器配置清单」**。
4. 导出的清单位于根目录下的 `exports/server_mod_manifest.json`。

---

### 第二步：在服务端（VPS / 本机服务器）注入并极速拉取

将生成的 `server_mod_manifest.json` 上传或复制到服务器本工具根目录下。

#### 场景 A：仅安全注入现有 `ServerName.ini`
执行配置写入，程序会自动备份原文件：
- **Windows**:
  ```bat
  start_server.bat -i "C:\Users\Administrator\Zomboid\Server\myserver.ini"
  ```
- **Linux**:
  ```bash
  chmod +x start_server.sh
  ./start_server.sh -i ~/Zomboid/Server/myserver.ini
  ```

#### 场景 B：注入配置并调用 SteamCMD 批量预载 Mod
追加 `-d` 参数，直接利用 SteamCMD 跑批拉取所有 Mod，极大缩减正式开服耗时：
- **Windows**:
  ```bat
  start_server.bat -i "myserver.ini" -d
  ```
- **Linux**:
  ```bash
  ./start_server.sh -i ~/Zomboid/Server/myserver.ini -d
  ```

---

## 📁 目录结构

```text
PZ-Server-ModManager/
├── core/
│   └── scanner.py             # Steam 盘符穿透与 Workshop ACF 逆向解析核心
├── exports/                   # 导出的清单成果目录
│   └── server_mod_manifest.json
├── client_extractor.py        # 客户端可视化 Web 服务器与 Mod 交互控制台
├── server_deployer.py         # 服务端 INI 注入引擎与 SteamCMD 任务调度器
├── start_client.bat           # [快捷] 客户端启动脚本 (Windows)
├── start_client.sh            # [快捷] 客户端启动脚本 (Linux/macOS)
├── start_server.bat           # [快捷] 服务端部署脚本 (Windows)
├── start_server.sh            # [快捷] 服务端部署脚本 (Linux/macOS)
├── requirements.txt           # 极轻依赖规范
└── README.md
```

---

## 🛠️ 进阶配置与调度

### `server_deployer.py` 完整参数说明

```text
选项:
  -m, --manifest PATH   指定清单路径 (默认: exports/server_mod_manifest.json)
  -i, --ini PATH        目标服务器配置 ini 文件路径
  -d, --download        配置注入完成后，立即唤起 SteamCMD 执行全量 Mod 批量预载
  -s, --steamcmd PATH   自定义 steamcmd 可执行程序绝对路径 (默认尝试从系统 PATH 解析)
  --no-backup           写入 ini 时禁用自动生成 .bak 备份副本
```

---

## 🦊 关于作者

* **Architecture & Refinement**：Crafted with precision by **Kitsune (狐玖)**.
* 追求干净自洽的系统调用、极低依赖体积与零冗余的代码边界。

---

## 📝 开源协议

本项目基于 [MIT License](LICENSE) 许可协议发布。