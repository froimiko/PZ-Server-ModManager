import http.server
import json
import os
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from core.scanner import PZScanner

PORT = 18888
EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

# 内存缓存当前扫描结果
SCANNED_MODS = []

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PZ Mod 提取与配置生成器</title>
    <style>
        :root {
            --vermilion: #b92b3a;
            --vermilion-dark: #8b1825;
            --vermilion-soft: #d33a4c;
            --sidebar-bg: #8c1d28;
            --sidebar-pattern: #781721;
            --paper-cream: #faf5ee;
            --paper-card: #ffffff;
            --sakura-pink: #f7cbd6;
            --sakura-subtle: #fcf1f4;
            --gold-accent: #c59b4e;
            --gold-soft: #dfbe79;
            --text-ink: #2c2225;
            --text-muted: #846f73;
            --border-cherry: #eed8de;
            --border-soft: #f2e6e8;
            --jade: #38a169;
            --jade-bg: #edfbf3;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: var(--paper-cream);
            color: var(--text-ink);
            height: 100vh;
            width: 100vw;
            overflow: hidden;
            display: flex;
            align-items: stretch;
            justify-content: stretch;
            padding: 0;
            margin: 0;
        }
        /* 主窗体：铺满全屏，空间无界 */
        .window-frame {
            display: flex;
            width: 100%;
            height: 100vh;
            background: var(--paper-cream);
            border-radius: 0;
            overflow: hidden;
            border: none;
            box-shadow: none;
            position: relative;
        }
        /* 左侧赤朱侧边栏 */
        .sidebar {
            width: 96px;
            background: linear-gradient(180deg, var(--sidebar-bg) 0%, var(--vermilion-dark) 100%);
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 26px 0;
            position: relative;
            flex-shrink: 0;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        .sidebar::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(circle at 50% 20%, rgba(255,255,255,0.08), transparent 70%);
            pointer-events: none;
        }
        .crest-icon {
            width: 52px;
            height: 52px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 36px;
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            cursor: pointer;
            transition: transform 0.2s ease;
        }
        .crest-icon:hover { transform: scale(1.06); }
        .nav-list {
            display: flex;
            flex-direction: column;
            gap: 16px;
            width: 100%;
            align-items: center;
        }
        .nav-item {
            width: 78px;
            height: 48px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgba(255, 255, 255, 0.75);
            font-size: 20px;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }
        .nav-item:hover {
            color: #fff;
            background: rgba(255, 255, 255, 0.12);
        }
        .nav-item.active {
            color: var(--vermilion);
            background: var(--paper-cream);
            box-shadow: -4px 4px 14px rgba(0, 0, 0, 0.12);
            font-weight: bold;
        }
        .sidebar-bottom {
            margin-top: auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 16px;
        }

        /* 右侧主体卷轴内容 */
        .main-stage {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 28px 36px;
            overflow-y: auto;
            background: radial-gradient(circle at 90% 10%, #fffbf8 0%, var(--paper-cream) 70%);
        }
        
        /* 顶部落樱富士风雅横幅 */
        .banner-art {
            width: 100%;
            height: 120px;
            border-radius: 18px;
            background: linear-gradient(135deg, #fcdde4 0%, #fbe8ec 40%, #e8f0fe 80%, #fed8df 100%);
            border: 1px solid var(--border-cherry);
            padding: 20px 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: relative;
            overflow: hidden;
            margin-bottom: 22px;
            box-shadow: 0 4px 16px rgba(220, 160, 175, 0.15);
        }
        .banner-art::before {
            content: '🌸 ⛩️ 富士雪霽 · 櫻落神社 🌸';
            position: absolute;
            right: 24px;
            bottom: 12px;
            font-size: 13px;
            color: rgba(185, 43, 58, 0.35);
            font-weight: 600;
            letter-spacing: 2px;
        }
        .banner-text h2 {
            font-size: 22px;
            color: var(--vermilion-dark);
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }
        .banner-text p {
            font-size: 13px;
            color: var(--text-muted);
        }
        .banner-badge {
            background: var(--paper-card);
            padding: 6px 14px;
            border-radius: 20px;
            border: 1px solid var(--border-cherry);
            font-size: 12px;
            font-weight: 600;
            color: var(--vermilion);
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        /* 顶部神社分类标签按钮 */
        .jinja-tabs {
            display: flex;
            gap: 12px;
            margin-bottom: 20px;
        }
        .jinja-tab {
            flex: 1;
            padding: 10px 14px;
            background: var(--paper-card);
            border: 1px solid var(--border-cherry);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-size: 13.5px;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        }
        .jinja-tab:hover {
            border-color: var(--vermilion-soft);
            color: var(--vermilion);
            transform: translateY(-1px);
        }
        .jinja-tab.active {
            background: #fff;
            border: 2px solid var(--vermilion);
            color: var(--vermilion);
            box-shadow: 0 4px 12px rgba(185, 43, 58, 0.12);
        }

        /* 手动路径与工坊操作栏 */
        .path-box {
            background: var(--paper-card);
            border: 1px solid var(--border-cherry);
            border-radius: 16px;
            padding: 14px 18px;
            margin-bottom: 16px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
        }
        .path-box-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .path-input-group {
            display: flex;
            gap: 10px;
        }
        .path-input-group input {
            flex: 1;
            padding: 10px 15px;
            border-radius: 10px;
            border: 1px solid var(--border-cherry);
            background: var(--sakura-subtle);
            color: var(--text-ink);
            outline: none;
            font-size: 13px;
            transition: border-color 0.2s ease;
        }
        .path-input-group input:focus {
            border-color: var(--vermilion);
            background: #fff;
        }

        /* 搜索栏与操作按键 */
        .controls-row {
            display: flex;
            gap: 12px;
            align-items: center;
            margin-bottom: 16px;
        }
        .search-container {
            flex: 1;
            position: relative;
        }
        .search-container input {
            width: 100%;
            padding: 10px 16px;
            border-radius: 12px;
            border: 1px solid var(--border-cherry);
            background: #ffffff;
            color: var(--text-ink);
            font-size: 13.5px;
            outline: none;
            transition: all 0.2s ease;
        }
        .search-container input:focus {
            border-color: var(--vermilion);
            box-shadow: 0 0 10px rgba(211, 58, 76, 0.15);
        }
        
        button {
            padding: 9px 18px;
            border-radius: 11px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-vermilion {
            background: linear-gradient(135deg, var(--vermilion) 0%, var(--vermilion-soft) 100%);
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(185, 43, 58, 0.28);
        }
        .btn-vermilion:hover {
            background: linear-gradient(135deg, var(--vermilion-dark) 0%, var(--vermilion) 100%);
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(185, 43, 58, 0.38);
        }
        .btn-outline {
            background: var(--paper-card);
            border: 1px solid var(--border-cherry);
            color: var(--text-ink);
        }
        .btn-outline:hover {
            border-color: var(--vermilion);
            color: var(--vermilion);
            background: var(--sakura-subtle);
            transform: translateY(-1px);
        }

        /* 统计与状态 */
        .status-strip {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12.5px;
            color: var(--text-muted);
            margin-bottom: 12px;
            padding: 0 4px;
        }
        .status-strip .counter-num {
            color: var(--vermilion);
            font-weight: 700;
            font-size: 14px;
        }

        /* 模组列表与卡片 */
        .mod-list {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 10px;
            overflow-y: auto;
            min-height: 0;
            padding-right: 8px;
        }
        .mod-list::-webkit-scrollbar { width: 6px; }
        .mod-list::-webkit-scrollbar-thumb {
            background: #e4c8cf;
            border-radius: 4px;
        }
        .mod-list::-webkit-scrollbar-thumb:hover { background: var(--vermilion-soft); }

        .mod-card {
            background: #ffffff;
            border: 1px solid var(--border-cherry);
            border-radius: 14px;
            padding: 13px 18px;
            display: flex;
            align-items: center;
            gap: 16px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
        }
        .mod-card::before {
            content: '';
            position: absolute;
            left: 0;
            top: 20%;
            bottom: 20%;
            width: 3px;
            background: transparent;
            border-radius: 0 3px 3px 0;
            transition: background 0.2s ease;
        }
        .mod-card:hover {
            border-color: var(--sakura-pink);
            transform: translateX(2px);
            box-shadow: 0 4px 14px rgba(185, 43, 58, 0.08);
        }
        .mod-card:hover::before {
            background: var(--vermilion);
        }
        .mod-card.disabled {
            opacity: 0.55;
            background: #fbf9f9;
        }
        .mod-card input[type="checkbox"] {
            width: 19px;
            height: 19px;
            accent-color: var(--vermilion);
            cursor: pointer;
        }
        .mod-info { flex: 1; min-width: 0; }
        .mod-name-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
            flex-wrap: wrap;
        }
        .mod-name {
            font-weight: 600;
            font-size: 14px;
            color: var(--text-ink);
        }
        .badge {
            font-size: 11px;
            padding: 2px 7px;
            border-radius: 6px;
            font-weight: 600;
            line-height: 1.4;
            display: inline-flex;
            align-items: center;
            gap: 3px;
        }
        .badge-warn {
            background: #fff7e6;
            color: #d46b08;
            border: 1px solid #ffd591;
        }
        .badge-id {
            background: var(--sakura-subtle);
            color: var(--vermilion-dark);
            border: 1px solid var(--border-cherry);
            font-family: 'Fira Code', Consolas, monospace;
            font-size: 11px;
        }
        .mod-meta {
            font-size: 12px;
            color: var(--text-muted);
            display: flex;
            gap: 14px;
            align-items: center;
        }
        .workshop-link {
            color: var(--vermilion);
            text-decoration: none;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 9px;
            border-radius: 8px;
            background: var(--sakura-subtle);
            border: 1px solid var(--border-cherry);
            transition: all 0.2s ease;
        }
        .workshop-link:hover {
            background: var(--vermilion);
            color: #fff;
            border-color: var(--vermilion);
        }
        #toast {
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 12px 22px;
            background: var(--vermilion);
            color: #fff;
            border-radius: 12px;
            font-size: 13.5px;
            font-weight: 600;
            display: none;
            box-shadow: 0 8px 24px rgba(185, 43, 58, 0.35);
            animation: slideUp 0.3s ease-out;
            z-index: 999;
        }
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="window-frame">
        <!-- 左侧赤朱侧栏 -->
        <aside class="sidebar">
            <div class="crest-icon" title="狐玖巫女之印">🌸</div>
            <nav class="nav-list">
                <div class="nav-item active" title="模组提取总览">⛩️</div>
                <div class="nav-item" title="工坊穿透与扫描" onclick="document.getElementById('customPathInput').focus()">📂</div>
                <div class="nav-item" title="全选/清空配置" onclick="toggleAll(true)">✨</div>
                <div class="nav-item" title="重新探测" onclick="rescan()">🔄</div>
            </nav>
            <div class="sidebar-bottom">
                <div class="nav-item" title="导出服务器配置" onclick="exportConfig()" style="color: var(--gold-soft);">💾</div>
            </div>
        </aside>

        <!-- 右侧主舞台画卷 -->
        <main class="main-stage">
            <!-- 顶部富士雪霁和风横幅 -->
            <div class="banner-art">
                <div class="banner-text">
                    <h2>
                        <span>⛩️ 僵尸毁灭工程 Mod 配置萃取仪</span>
                    </h2>
                    <p>落樱如霰 · 自动穿透多盘 Steam 创意工坊 · 提取服务端专用 mod.info 与 WorkshopID</p>
                </div>
                <div class="banner-badge">
                    <span>和风庭院</span>
                </div>
            </div>

            <!-- 神社五段分类标签 (复刻图片风格) -->
            <div class="jinja-tabs">
                <div class="jinja-tab active" onclick="setTabFilter('all', this)">⛩️ 全部模组</div>
                <div class="jinja-tab" onclick="setTabFilter('normal', this)">🌸 常规模组</div>
                <div class="jinja-tab" onclick="setTabFilter('client', this)">🏮 客户端补丁/汉化</div>
                <div class="jinja-tab" onclick="setTabFilter('active', this)">🦊 仅看已勾选</div>
                <div class="jinja-tab" onclick="setTabFilter('inactive', this)">🍂 未启用模组</div>
            </div>

            <!-- 手动路径 / 探测状态栏 -->
            <div class="path-box">
                <div class="path-box-header">
                    <span style="font-weight: 600; color: var(--vermilion-dark); display: flex; align-items: center; gap: 6px;">
                        📂 Steam 创意工坊与模组目录
                    </span>
                    <span id="current-scan-path" style="font-size: 12px; color: var(--text-muted); font-family: monospace;">正在感知路径...</span>
                </div>
                <div class="path-input-group">
                    <input type="text" id="customPathInput" placeholder="输入工坊路径 (如 D:\\Steam\\steamapps\\workshop\\content\\108600) 或任意 Mod 文件夹...">
                    <button class="btn-outline" onclick="scanCustomPath()">🔍 载入此路径</button>
                    <button class="btn-outline" onclick="rescan()">🔄 全盘重探</button>
                </div>
            </div>

            <!-- 控制与搜索栏 -->
            <div class="controls-row">
                <div class="search-container">
                    <input type="text" id="search" placeholder="🔍 键入名称、ModID 或 WorkshopID 进行即时筛选..." oninput="filterMods()">
                </div>
                <button class="btn-outline" onclick="toggleAll(true)">✓ 全选</button>
                <button class="btn-outline" onclick="toggleAll(false)">✗ 全清</button>
                <button class="btn-vermilion" onclick="exportConfig()">💾 导出清单</button>
            </div>

            <!-- 统计与说明 -->
            <div class="status-strip">
                <span id="stat-count">正在查阅模组卷轴...</span>
                <span>✦ 温馨提示：带 🏮 标记的汉化或界面类 Mod，可酌情取消勾选以轻量化服务端</span>
            </div>

            <!-- 模组卷轴列表 -->
            <div class="mod-list" id="modList"></div>
        </main>
    </div>

    <div id="toast">导出成功！</div>

    <script>
        let allMods = [];

        async function loadMods() {
            try {
                const statusRes = await fetch('/api/status');
                const statusData = await statusRes.json();
                updatePathStatus(statusData);

                const res = await fetch('/api/mods');
                allMods = await res.json();
                renderMods(allMods);
            } catch (err) {
                console.error("加载失败", err);
            }
        }

        function updatePathStatus(data) {
            const el = document.getElementById('current-scan-path');
            if (!el) return;
            if (data.active_paths && data.active_paths.length > 0) {
                el.innerText = `当前目录: ${data.active_paths.join('; ')}`;
                el.style.color = 'var(--jade-green)';
            } else {
                el.innerText = `⚠️ 未自动探测到工坊目录，请在下方手动填入`;
                el.style.color = 'var(--gold-accent)';
            }
        }

        async function scanCustomPath() {
            const pathVal = document.getElementById('customPathInput').value.trim();
            if (!pathVal) {
                showToast("⚠️ 请先输入有效的目录路径");
                return;
            }
            document.getElementById('stat-count').innerText = '正在扫描指定路径...';
            try {
                const res = await fetch('/api/scan_path', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: pathVal })
                });
                const result = await res.json();
                if (result.status === "error") {
                    showToast(`❌ ${result.message}`);
                    document.getElementById('stat-count').innerText = `扫描失败: ${result.message}`;
                    return;
                }
                allMods = result.mods;
                renderMods(allMods);
                showToast(`🎉 成功载入 ${allMods.length} 个模组！`);
                updatePathStatus({ active_paths: [pathVal] });
            } catch (err) {
                showToast(`❌ 网络请求失败`);
            }
        }

        function renderMods(mods) {
            const list = document.getElementById('modList');
            list.innerHTML = '';
            
            const activeCount = allMods.filter(m => m.enabled).length;
            document.getElementById('stat-count').innerHTML = `已勾选 <span class="highlight-count">${activeCount}</span> / 总计 ${allMods.length} 个模组`;

            if (mods.length === 0) {
                list.innerHTML = `
                    <div style="text-align: center; padding: 40px 20px; color: var(--text-dim); background: var(--card-bg); border-radius: 12px; border: 1px dashed var(--border-dim);">
                        <div style="font-size: 28px; margin-bottom: 10px;">🍃</div>
                        <div style="font-size: 15px; color: #fff; margin-bottom: 6px;">未发现任何 Mod</div>
                        <div style="font-size: 13px;">请检查 Steam 是否下载完 Mod，或在上方的自定义输入栏填入真实路径~</div>
                    </div>
                `;
                return;
            }

            mods.forEach(mod => {
                const card = document.createElement('div');
                card.className = `mod-card ${mod.enabled ? '' : 'disabled'}`;
                
                let badges = '';
                if (mod.client_only_suspect) {
                    badges += `<span class="badge badge-warn" title="包含UI/汉化/音效关键词，服务器可能不需要强制安装">疑似客户端专用</span>`;
                }

                card.innerHTML = `
                    <input type="checkbox" ${mod.enabled ? 'checked' : ''} onchange="toggleMod('${mod.mod_id}', this.checked)">
                    <div class="mod-info">
                        <div class="mod-name-row">
                            <span class="mod-name">${escapeHtml(mod.name)}</span>
                            ${badges}
                        </div>
                        <div class="mod-meta">
                            <span class="badge-id">ModID: ${escapeHtml(mod.mod_id)}</span>
                            <span>工坊ID: ${mod.workshop_id || '本地Mod'}</span>
                        </div>
                    </div>
                    ${mod.url ? `<a href="${mod.url}" target="_blank" class="workshop-link">🔗 查看工坊</a>` : ''}
                `;
                list.appendChild(card);
            });
        }

        function escapeHtml(text) {
            return (text || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        function toggleMod(modId, state) {
            const target = allMods.find(m => m.mod_id === modId);
            if (target) {
                target.enabled = state;
            }
            filterMods();
        }

        function toggleAll(state) {
            allMods.forEach(m => m.enabled = state);
            filterMods();
        }

        let currentTabFilter = 'all';

        function setTabFilter(type, el) {
            currentTabFilter = type;
            document.querySelectorAll('.jinja-tab').forEach(t => t.classList.remove('active'));
            if (el) el.classList.add('active');
            filterMods();
        }

        function filterMods() {
            const q = document.getElementById('search').value.toLowerCase().trim();
            const filtered = allMods.filter(m => {
                const matchQuery = m.name.toLowerCase().includes(q) ||
                                   m.mod_id.toLowerCase().includes(q) ||
                                   (m.workshop_id && m.workshop_id.includes(q));
                if (!matchQuery) return false;

                if (currentTabFilter === 'active') return m.enabled;
                if (currentTabFilter === 'inactive') return !m.enabled;
                if (currentTabFilter === 'client') return m.client_only_suspect;
                if (currentTabFilter === 'normal') return !m.client_only_suspect;
                return true;
            });
            renderMods(filtered);
        }

        async function rescan() {
            document.getElementById('stat-count').innerText = '正在全盘自动重新探测...';
            try {
                const res = await fetch('/api/rescan', { method: 'POST' });
                allMods = await res.json();
                renderMods(allMods);
                const statusRes = await fetch('/api/status');
                const statusData = await statusRes.json();
                updatePathStatus(statusData);
                showToast(`🔄 自动探测完成，找到 ${allMods.length} 个 Mod`);
            } catch (err) {
                showToast("❌ 重新探测失败");
            }
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => toast.style.display = 'none', 3500);
        }

        async function exportConfig() {
            const enabledMods = allMods.filter(m => m.enabled);
            const res = await fetch('/api/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(enabledMods)
            });
            const data = await res.json();
            const toast = document.getElementById('toast');
            toast.innerText = `✅ 已成功导出到: ${data.path}`;
            toast.style.display = 'block';
            setTimeout(() => toast.style.display = 'none', 4000);
        }

        window.onload = loadMods;
    </script>
</body>
</html>
"""

class ModExtractorHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # 静默常规访问日志，只保留终端纯净
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/mods":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            data = [m.to_dict() for m in SCANNED_MODS]
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            status_data = {
                "active_paths": [str(p) for p in ACTIVE_PATHS],
                "total_mods": len(SCANNED_MODS)
            }
            self.wfile.write(json.dumps(status_data, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        global SCANNED_MODS, ACTIVE_PATHS
        if self.path == "/api/rescan":
            SCANNED_MODS = scan_local()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps([m.to_dict() for m in SCANNED_MODS], ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/scan_path":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            req = json.loads(body.decode("utf-8"))
            custom_str = req.get("path", "").strip().strip('\"').strip('\'')
            target_p = Path(custom_str)
            if not target_p.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": f"路径不存在: {custom_str}"}, ensure_ascii=False).encode("utf-8"))
                return

            found = PZScanner.scan_any_directory(target_p)
            SCANNED_MODS = found
            ACTIVE_PATHS = [target_p]

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "mods": [m.to_dict() for m in SCANNED_MODS]
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/export":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            enabled_mods = json.loads(body.decode("utf-8"))
            
            # 提取去重的 workshop_items 和 mods 列表
            workshop_ids = []
            mod_ids = []
            for item in enabled_mods:
                m_id = item.get("mod_id")
                w_id = item.get("workshop_id")
                if m_id and m_id not in mod_ids:
                    mod_ids.append(m_id)
                if w_id and w_id not in workshop_ids:
                    workshop_ids.append(w_id)

            export_data = {
                "server_formatted": {
                    "Mods": ";".join(mod_ids),
                    "WorkshopItems": ";".join(workshop_ids)
                },
                "total_mods": len(mod_ids),
                "total_workshops": len(workshop_ids),
                "details": enabled_mods
            }
            
            out_file = EXPORT_DIR / "server_mod_manifest.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "path": str(out_file)}).encode("utf-8"))

ACTIVE_PATHS = []

def scan_local():
    global ACTIVE_PATHS
    paths = PZScanner.detect_steam_workshop_paths()
    ACTIVE_PATHS = paths
    mods = []
    seen = set()
    for p in paths:
        found = PZScanner.scan_any_directory(p)
        for m in found:
            if m.mod_id not in seen:
                seen.add(m.mod_id)
                mods.append(m)
    return mods

def main():
    global SCANNED_MODS
    print("🦊 正在探测并扫描本地 Project Zomboid 创意工坊与本地 Mod...")
    SCANNED_MODS = scan_local()
    if ACTIVE_PATHS:
        for p in ACTIVE_PATHS:
            print(f"  📂 命中目录: {p}")
    else:
        print("  ⚠️ 未能自动探测到工坊目录，可在稍后打开的网页中手动粘贴路径。")
    print(f"✅ 扫描完成，发现 {len(SCANNED_MODS)} 个可用 Mod。")
    print(f"🚀 启动提取器面板: http://127.0.0.1:{PORT}")

    class ReuseTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    server = ReuseTCPServer(("127.0.0.1", PORT), ModExtractorHandler)
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 提取器已安全关闭。")

if __name__ == "__main__":
    main()