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
    <title>PZ Mod 提取与配置生成器 - 狐玖终端</title>
    <style>
        :root {
            --crimson: #e62e43;
            --crimson-hover: #c9182d;
            --crimson-glow: rgba(230, 46, 67, 0.35);
            --pure-white: #ffffff;
            --silk-white: #fcf8fa;
            --soft-pink: #f9a8d4;
            --soft-pink-bg: rgba(249, 168, 212, 0.08);
            --obsidian-bg: #0d0c10;
            --card-bg: rgba(22, 19, 26, 0.92);
            --card-hover: rgba(30, 24, 35, 0.98);
            --border-dim: rgba(249, 168, 212, 0.14);
            --border-highlight: rgba(230, 46, 67, 0.4);
            --gold-accent: #f6c453;
            --gold-bg: rgba(246, 196, 83, 0.12);
            --gold-border: rgba(246, 196, 83, 0.35);
            --jade-green: #34d399;
            --jade-bg: rgba(52, 211, 153, 0.12);
            --jade-border: rgba(52, 211, 153, 0.3);
            --text-dim: #9ca3af;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            background: radial-gradient(circle at 15% 15%, #1f1522 0%, var(--obsidian-bg) 55%, #08080a 100%);
            color: var(--silk-white);
            padding: 28px 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
        }
        .container {
            width: 100%;
            max-width: 1100px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 22px;
            padding-bottom: 18px;
            border-bottom: 1px solid var(--border-dim);
            position: relative;
        }
        header::after {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 120px;
            height: 2px;
            background: linear-gradient(90deg, var(--crimson), var(--soft-pink), transparent);
        }
        .title-group h1 {
            font-size: 23px;
            color: var(--pure-white);
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: 0.5px;
        }
        .title-group h1 .brand-badge {
            font-size: 11px;
            font-weight: 700;
            color: var(--crimson);
            background: #fff;
            padding: 2px 7px;
            border-radius: 6px;
            letter-spacing: 0.8px;
            border: 1px solid var(--soft-pink);
            box-shadow: 0 0 10px rgba(255, 255, 255, 0.35);
        }
        .title-group p {
            font-size: 13px;
            color: var(--soft-pink);
            opacity: 0.85;
            margin-top: 5px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .actions { display: flex; gap: 10px; align-items: center; }
        button {
            padding: 9px 18px;
            border-radius: 9px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--crimson) 0%, #db2777 100%);
            color: var(--pure-white);
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 4px 14px var(--crimson-glow);
        }
        .btn-primary:hover {
            background: linear-gradient(135deg, var(--crimson-hover) 0%, #be185d 100%);
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(230, 46, 67, 0.5);
        }
        .btn-secondary {
            background: var(--card-bg);
            color: var(--silk-white);
            border: 1px solid var(--border-dim);
            backdrop-filter: blur(8px);
        }
        .btn-secondary:hover {
            background: var(--soft-pink-bg);
            border-color: var(--soft-pink);
            color: var(--pure-white);
            transform: translateY(-1px);
        }
        .search-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 18px;
        }
        .search-bar input {
            flex: 1;
            padding: 11px 16px;
            border-radius: 10px;
            border: 1px solid var(--border-dim);
            background: var(--card-bg);
            color: var(--pure-white);
            outline: none;
            font-size: 14px;
            transition: all 0.2s ease;
        }
        .search-bar input:focus {
            border-color: var(--soft-pink);
            box-shadow: 0 0 12px rgba(249, 168, 212, 0.2);
            background: rgba(28, 22, 33, 0.95);
        }
        .search-bar input::placeholder {
            color: #71717a;
        }
        .mod-stats {
            font-size: 13px;
            color: var(--text-dim);
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 4px;
        }
        .mod-stats .highlight-count {
            color: var(--gold-accent);
            font-weight: 600;
        }
        .mod-list {
            display: flex;
            flex-direction: column;
            gap: 9px;
            max-height: 64vh;
            overflow-y: auto;
            padding-right: 6px;
        }
        .mod-list::-webkit-scrollbar { width: 6px; }
        .mod-list::-webkit-scrollbar-thumb {
            background: rgba(249, 168, 212, 0.25);
            border-radius: 4px;
        }
        .mod-list::-webkit-scrollbar-thumb:hover {
            background: var(--soft-pink);
        }
        .mod-card {
            background: var(--card-bg);
            border: 1px solid var(--border-dim);
            border-radius: 12px;
            padding: 13px 18px;
            display: flex;
            align-items: center;
            gap: 15px;
            transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            backdrop-filter: blur(10px);
        }
        .mod-card::before {
            content: '';
            position: absolute;
            left: 0;
            top: 15%;
            bottom: 15%;
            width: 3px;
            border-radius: 0 3px 3px 0;
            background: transparent;
            transition: background 0.2s ease;
        }
        .mod-card:hover {
            background: var(--card-hover);
            border-color: rgba(249, 168, 212, 0.35);
            transform: translateX(2px);
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
        }
        .mod-card:hover::before {
            background: linear-gradient(180deg, var(--crimson), var(--soft-pink));
        }
        .mod-card.disabled {
            opacity: 0.45;
            filter: grayscale(40%);
        }
        .mod-card input[type="checkbox"] {
            width: 19px;
            height: 19px;
            accent-color: var(--crimson);
            cursor: pointer;
            border-radius: 4px;
        }
        .mod-info { flex: 1; min-width: 0; }
        .mod-name-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 5px;
            flex-wrap: wrap;
        }
        .mod-name {
            font-weight: 600;
            font-size: 14.5px;
            color: var(--pure-white);
            letter-spacing: 0.2px;
        }
        .badge {
            font-size: 11px;
            padding: 2px 7px;
            border-radius: 5px;
            font-weight: 600;
            line-height: 1.4;
            display: inline-flex;
            align-items: center;
            gap: 3px;
        }
        .badge-warn {
            background: var(--gold-bg);
            color: var(--gold-accent);
            border: 1px solid var(--gold-border);
        }
        .badge-id {
            background: var(--jade-bg);
            color: var(--jade-green);
            border: 1px solid var(--jade-border);
            font-family: 'Fira Code', Consolas, monospace;
            font-size: 11.5px;
        }
        .mod-meta {
            font-size: 12px;
            color: var(--text-dim);
            display: flex;
            gap: 14px;
            align-items: center;
            flex-wrap: wrap;
        }
        .workshop-link {
            color: var(--soft-pink);
            text-decoration: none;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 9px;
            border-radius: 6px;
            background: rgba(249, 168, 212, 0.08);
            border: 1px solid rgba(249, 168, 212, 0.2);
            transition: all 0.2s ease;
        }
        .workshop-link:hover {
            background: rgba(249, 168, 212, 0.18);
            border-color: var(--soft-pink);
            color: #fff;
            transform: translateY(-1px);
        }
        #toast {
            position: fixed;
            bottom: 28px;
            right: 28px;
            padding: 13px 24px;
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            color: #fff;
            border: 1px solid var(--jade-border);
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            display: none;
            box-shadow: 0 8px 24px rgba(16, 185, 129, 0.35);
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
    <div class="container">
        <header>
            <div class="title-group">
                <h1>
                    <span>🦊 PZ Mod 提取配置面板</span>
                    <span class="brand-badge">KITSUNE UI</span>
                </h1>
                <p>🌸 勾选需要部署到服务器的 Mod · 自动穿透多盘符工坊 · 智能标记客户端补丁</p>
            </div>
            <div class="actions">
                <button class="btn-secondary" onclick="toggleAll(true)">✓ 全选</button>
                <button class="btn-secondary" onclick="toggleAll(false)">✗ 全清</button>
                <button class="btn-primary" onclick="exportConfig()">💾 导出服务器清单</button>
            </div>
        </header>

        <div class="custom-path-bar" style="background: var(--card-bg); border: 1px solid var(--border-dim); border-radius: 12px; padding: 12px 16px; margin-bottom: 14px; display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; align-items: center; justify-content: space-between; font-size: 13px;">
                <span style="color: var(--soft-pink); font-weight: 600; display: flex; align-items: center; gap: 6px;">
                    📂 手动指定 Mod 路径 / 工坊目录
                </span>
                <span id="current-scan-path" style="font-size: 12px; color: var(--text-dim); font-family: monospace;">正在加载路径状态...</span>
            </div>
            <div style="display: flex; gap: 10px;">
                <input type="text" id="customPathInput" placeholder="输入工坊路径 (如 D:\\SteamLibrary\\steamapps\\workshop\\content\\108600) 或任意 Mod 文件夹..." style="flex: 1; padding: 9px 14px; border-radius: 8px; border: 1px solid var(--border-dim); background: rgba(13, 12, 16, 0.7); color: #fff; outline: none; font-size: 13px;">
                <button class="btn-secondary" style="border-color: var(--border-highlight);" onclick="scanCustomPath()">🔍 载入此路径</button>
                <button class="btn-secondary" onclick="rescan()">🔄 全盘自动重探</button>
            </div>
        </div>

        <div class="search-bar">
            <input type="text" id="search" placeholder="🔍 搜索 Mod 名称、ModID 或 创意工坊 ID..." oninput="filterMods()">
        </div>

        <div class="mod-stats">
            <span id="stat-count">正在加载 Mod 列表...</span>
            <span style="color: var(--soft-pink); opacity: 0.9;">✦ 提示：UI/汉化/音效等客户端专用 Mod 建议取消勾选，以轻量化服务端启动</span>
        </div>
        <div class="mod-list" id="modList"></div>
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

        function filterMods() {
            const q = document.getElementById('search').value.toLowerCase().trim();
            const filtered = allMods.filter(m => {
                return m.name.toLowerCase().includes(q) ||
                       m.mod_id.toLowerCase().includes(q) ||
                       (m.workshop_id && m.workshop_id.includes(q));
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