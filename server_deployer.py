import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PZ_APP_ID = "108600"

class ServerDeployer:
    def __init__(self, manifest_path: str, ini_path: str, steamcmd_path: str = None):
        self.manifest_path = Path(manifest_path)
        self.ini_path = Path(ini_path) if ini_path else None
        self.steamcmd_path = steamcmd_path or shutil.which("steamcmd")
        self.is_windows = platform.system() == "Windows"

    def load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"找不到导出的 Mod 清单文件: {self.manifest_path}")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def inject_ini(self, backup: bool = True):
        """将导出的 Mods 与 WorkshopItems 安全注入到指定 INI 中"""
        if not self.ini_path or not self.ini_path.exists():
            print(f"⚠️ 未指定有效的 ini 文件路径，跳过 ini 注入。")
            return

        manifest = self.load_manifest()
        new_mods = manifest.get("server_formatted", {}).get("Mods", "")
        new_workshops = manifest.get("server_formatted", {}).get("WorkshopItems", "")

        if backup:
            bak = self.ini_path.with_suffix(self.ini_path.suffix + ".bak")
            shutil.copy2(self.ini_path, bak)
            print(f"🛡️ 已备份原 ini 到: {bak}")

        with open(self.ini_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        mods_written = False
        workshop_written = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Mods="):
                new_lines.append(f"Mods={new_mods}\n")
                mods_written = True
            elif stripped.startswith("WorkshopItems="):
                new_lines.append(f"WorkshopItems={new_workshops}\n")
                workshop_written = True
            else:
                new_lines.append(line)

        if not mods_written:
            new_lines.append(f"\nMods={new_mods}\n")
        if not workshop_written:
            new_lines.append(f"WorkshopItems={new_workshops}\n")

        with open(self.ini_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"✅ 成功注入配置到 {self.ini_path}:")
        print(f"   - Mods: {manifest.get('total_mods', 0)} 个")
        print(f"   - WorkshopItems: {manifest.get('total_workshops', 0)} 个")

    def generate_steamcmd_script(self, install_dir: str = None) -> Path:
        """生成供 SteamCMD 执行的批量下载脚本"""
        manifest = self.load_manifest()
        workshops = manifest.get("server_formatted", {}).get("WorkshopItems", "").split(";")
        workshops = [w.strip() for w in workshops if w.strip()]

        script_path = Path("steamcmd_download.txt")
        lines = ["@ShutdownOnFailedCommand 0", "@NoPromptForPassword 1"]
        if install_dir:
            lines.append(f'force_install_dir "{install_dir}"')
        lines.append("login anonymous")
        for wid in workshops:
            # workshop_download_item <appid> <workshop_id> validate
            lines.append(f"workshop_download_item {PZ_APP_ID} {wid} validate")
        lines.append("quit\n")

        with open(script_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"📝 SteamCMD 批量拉取脚本已生成: {script_path.resolve()} (共 {len(workshops)} 个工坊项目)")
        return script_path

    def download_with_steamcmd(self, install_dir: str = None):
        """调用 SteamCMD 批量执行静默下载"""
        if not self.steamcmd_path:
            print("❌ 未在系统 PATH 中找到 steamcmd，请通过 --steamcmd 指定可执行文件路径！")
            return

        script_file = self.generate_steamcmd_script(install_dir)
        cmd = [self.steamcmd_path, "+runscript", str(script_file.resolve())]
        print(f"🚀 正在调用 SteamCMD 执行批量拉取...")
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in p.stdout:
                if "Success" in line or "Downloading item" in line or "ERROR" in line:
                    print(f"  [SteamCMD] {line.strip()}")
            p.wait()
            if p.returncode == 0:
                print("🎉 所有工坊 Mod 下载与校验完成！")
            else:
                print(f"⚠️ SteamCMD 执行结束，退出码: {p.returncode}")
        except Exception as e:
            print(f"❌ 运行 SteamCMD 异常: {e}")

def main():
    parser = argparse.ArgumentParser(description="PZ 服务器 Mod 部署与 SteamCMD 自动下载器")
    parser.add_argument("-m", "--manifest", default="exports/server_mod_manifest.json", help="客户端导出的 JSON 清单路径")
    parser.add_argument("-i", "--ini", default=None, help="目标服务器 .ini 文件路径 (如 servertest.ini)")
    parser.add_argument("-d", "--download", action="store_true", help="是否立即调用 SteamCMD 拉取 Mod 文件")
    parser.add_argument("--steamcmd", default=None, help="steamcmd 可执行文件路径 (默认在系统 PATH 中查找)")
    parser.add_argument("--install-dir", default=None, help="指定 Mod 下载落盘的目标目录")

    args = parser.parse_args()
    deployer = ServerDeployer(args.manifest, args.ini, args.steamcmd)

    if args.ini:
        deployer.inject_ini()
    
    if args.download:
        deployer.download_with_steamcmd(args.install_dir)
    elif not args.ini:
        # 默认打印脚本
        deployer.generate_steamcmd_script(args.install_dir)

if __name__ == "__main__":
    main()