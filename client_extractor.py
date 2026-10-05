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
            --primary: #e11d48;
            --primary-hover: #be123c;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --accent: #38bdf8;
            --warn: #fbbf24;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif;
            background: var(--bg);
            color: var(--text-main);
            padding: 24px;
            display: flex;
            justify-content: center;
        }
        .container {
            width: 100%;
            max-width: 1080px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }
        .title-group h1 { font-size: 22px; color: #fff; display: flex; align-items: center; gap: 8px; }
        .title-group p { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
        .actions { display: flex; gap: 10px; align-items: center; }
        button {
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
        }
        .btn-primary { background: var(--primary); color: #fff; }
        .btn-primary:hover { background: var(--primary-hover); }
        .btn-secondary { background: var(--card-bg); color: var(--text-main); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--border); }
        .search-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
        }
        .search-bar input {
            flex: 1;
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            color: #fff;
            outline: none;
        }
        .mod-stats {
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
        }
        .mod-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 65vh;
            overflow-y: auto;
            padding-right: 6px;
        }
        .mod-list::-webkit-scrollbar { width: 6px; }
        .mod-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        .mod-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 14px;
            transition: border-color 0.2s;
        }
        .mod-card:hover { border-color: var(--primary); }
        .mod-card.disabled { opacity: 0.55; }
        .mod-card input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: var(--primary);
            cursor: pointer;
        }
        .mod-info { flex: 1; min-width: 0; }
        .mod-name-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
        .mod-name { font-weight: 600; font-size: 14.5px; color: #fff; }
        .badge {
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }
        .badge-warn { background: rgba(251, 191, 36, 0.2); color: var(--warn); border: 1px solid rgba(251, 191, 36, 0.4); }
        .badge-id { background: rgba(56, 189, 248, 0.15); color: var(--accent); }
        .mod-meta { font-size: 12px; color: var(--text-muted); display: flex; gap: 12px; }
        .workshop-link {
            color: var(--accent);
            text-decoration: none;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            border-radius: 6px;
            background: rgba(56, 189, 248, 0.1);
        }
        .workshop-link:hover { text-decoration: underline; }
        #toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 12px 20px;
            background: #10b981;
            color: #fff;
            border-radius: 8px;
            font-size: 14px;
            display: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="title-group">
                <h1>🦊 PZ Mod 提取配置面板</h1>
                <p>勾选需要部署到服务器的 Mod，已智能标记疑似客户端专用/汉化补丁</p>
            </div>
            <div class="actions">
                <button class="btn-secondary" onclick="toggleAll(true)">全选</button>
                <button class="btn-secondary" onclick="toggleAll(false)">反选/全清</button>
                <button class="btn-primary" onclick="exportConfig()">💾 导出为服务器配置清单</button>
            </div>
        </header>

        <div class="search-bar">
            <input type="text" id="search" placeholder="搜索 Mod 名字、ModID 或 创意工坊 ID..." oninput="filterMods()">
            <button class="btn-secondary" onclick="rescan()">🔄 重新扫描本地工坊</button>
        </div>

        <div class="mod-stats">
            <span id="stat-count">正在加载 Mod 列表...</span>
            <span>💡 提示：纯UI或音效类Mod取消勾选可减轻服务端负载</span>
        </div>

        <div class="mod-list" id="modList"></div>
    </div>

    <div id="toast">导出成功！</div>

    <script>
        let allMods = [];

        async function loadMods() {
            const res = await fetch('/api/mods');
            allMods = await res.json();
            renderMods(allMods);
        }

        function renderMods(mods) {
            const list = document.getElementById('modList');
            list.innerHTML = '';
            
            const activeCount = allMods.filter(m => m.enabled).length;
            document.getElementById('stat-count').innerText = `已选 ${activeCount} / 总共 ${allMods.length} 个 Mod`;

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
            document.getElementById('stat-count').innerText = '正在重新扫描...';
            const res = await fetch('/api/rescan', { method: 'POST' });
            allMods = await res.json();
            renderMods(allMods);
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
        else:
            self.send_error(404)

    def do_POST(self):
        global SCANNED_MODS
        if self.path == "/api/rescan":
            SCANNED_MODS = scan_local()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps([m.to_dict() for m in SCANNED_MODS], ensure_ascii=False).encode("utf-8"))
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

def scan_local():
    paths = PZScanner.detect_steam_workshop_paths()
    mods = []
    seen = set()
    for p in paths:
        found = PZScanner.scan_workshop_mods(p)
        for m in found:
            if m.mod_id not in seen:
                seen.add(m.mod_id)
                mods.append(m)
    return mods

def main():
    global SCANNED_MODS
    print("🦊 正在探测并扫描本地 Project Zomboid 创意工坊 Mod...")
    SCANNED_MODS = scan_local()
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