import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

class PZModInfo:
    def __init__(self, mod_id: str, name: str, workshop_id: Optional[str] = None, 
                 description: str = "", url: str = "", path: str = ""):
        self.mod_id = mod_id
        self.name = name
        self.workshop_id = workshop_id
        self.description = description
        self.url = url or (f"https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}" if workshop_id else "")
        self.path = path
        # 客户端专用常见启发式标记（包含UI/sound/texture/radio替换等且无服务端逻辑时）
        self.is_client_only_suspect = self._detect_client_only()

    def _detect_client_only(self) -> bool:
        lower_name = self.name.lower()
        lower_id = self.mod_id.lower()
        suspect_keywords = ["translation", "translate", "汉化", "语言包", "minimap", "hud", "ui", "music", "soundpack"]
        for kw in suspect_keywords:
            if kw in lower_name or kw in lower_id:
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "mod_id": self.mod_id,
            "name": self.name,
            "workshop_id": self.workshop_id,
            "description": self.description,
            "url": self.url,
            "client_only_suspect": self.is_client_only_suspect,
            "enabled": True
        }

class PZScanner:
    """负责扫描本地客户端已订阅Mod、mod.info元数据与INI配置"""
    
    @staticmethod
    def get_default_zomboid_dir() -> Path:
        """获取本地用户目录下的 Zomboid 目录"""
        if sys.platform == "win32":
            return Path(os.environ.get("USERPROFILE", "C:/")) / "Zomboid"
        return Path.home() / "Zomboid"

    @staticmethod
    def detect_steam_workshop_paths() -> List[Path]:
        """尝试自动探测 PZ 创意工坊存放目录 (108600) 及本地 mods 目录"""
        candidates = []
        if sys.platform == "win32":
            # 扩展 A-Z 所有盘符全量探测
            drives = [f"{chr(d)}:/" for d in range(ord('C'), ord('Z') + 1)] + ["A:/", "B:/"]
            for drive in drives:
                candidates.append(Path(drive) / "SteamLibrary" / "steamapps" / "workshop" / "content" / "108600")
                candidates.append(Path(drive) / "Steam" / "steamapps" / "workshop" / "content" / "108600")
                candidates.append(Path(drive) / "Program Files (x86)" / "Steam" / "steamapps" / "workshop" / "content" / "108600")
                candidates.append(Path(drive) / "Program Files" / "Steam" / "steamapps" / "workshop" / "content" / "108600")
        else:
            candidates.append(Path.home() / ".local/share/Steam/steamapps/workshop/content/108600")
            candidates.append(Path.home() / ".steam/steam/steamapps/workshop/content/108600")
            candidates.append(Path.home() / ".steam/root/steamapps/workshop/content/108600")

        # 同时加入本地用户文档目录下的 Zomboid/mods
        zomboid_mods = PZScanner.get_default_zomboid_dir() / "mods"
        if zomboid_mods.exists():
            candidates.append(zomboid_mods)

        return [p for p in candidates if p.exists() and p.is_dir()]

    @classmethod
    def scan_any_directory(cls, target_path: Path) -> List[PZModInfo]:
        """智能扫描任意指定目录：自动识别工坊 108600、包含 108600 的父层、或者纯本地 Mod 目录"""
        if not target_path or not target_path.exists():
            return []

        # 1. 如果用户指向了包含 108600 的上级目录，自动下探
        if (target_path / "108600").is_dir():
            return cls.scan_workshop_mods(target_path / "108600")
        if (target_path / "steamapps" / "workshop" / "content" / "108600").is_dir():
            return cls.scan_workshop_mods(target_path / "steamapps" / "workshop" / "content" / "108600")
        if (target_path / "workshop" / "content" / "108600").is_dir():
            return cls.scan_workshop_mods(target_path / "workshop" / "content" / "108600")

        # 2. 如果当前目录名就是 108600 或者子目录是纯数字，按工坊处理
        has_digit_dirs = any(p.is_dir() and p.name.isdigit() for p in target_path.iterdir() if p.is_dir())
        if target_path.name == "108600" or has_digit_dirs:
            return cls.scan_workshop_mods(target_path)

        # 3. 泛化遍历模式：深度搜索所有 mod.info
        discovered = []
        for root, _, files in os.walk(target_path):
            if "mod.info" in files:
                info_path = Path(root) / "mod.info"
                # 尝试从路径层次中提取纯数字的工坊ID
                workshop_id = None
                for part in reversed(info_path.parts[:-1]):
                    if part.isdigit() and len(part) >= 6:
                        workshop_id = part
                        break
                discovered.extend(cls.parse_mod_info_file(info_path, workshop_id=workshop_id))
        return discovered

    @classmethod
    def parse_mod_info_file(cls, info_file: Path, workshop_id: Optional[str] = None) -> List[PZModInfo]:
        """解析单一 mod.info 文本文件"""
        mods = []
        try:
            with open(info_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            return mods

        mod_id = ""
        name = ""
        desc = ""
        url = ""
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "id":
                    mod_id = v
                elif k == "name":
                    name = v
                elif k == "description":
                    desc = v
                elif k == "url":
                    url = v

        if mod_id:
            mods.append(PZModInfo(
                mod_id=mod_id,
                name=name or mod_id,
                workshop_id=workshop_id,
                description=desc,
                url=url,
                path=str(info_file.parent)
            ))
        return mods

    @classmethod
    def scan_workshop_mods(cls, workshop_root: Path) -> List[PZModInfo]:
        """全量扫描指定 workshop/content/108600 目录中的所有 Mod"""
        discovered = []
        if not workshop_root.exists():
            return discovered

        for item_dir in workshop_root.iterdir():
            if item_dir.is_dir() and item_dir.name.isdigit():
                workshop_id = item_dir.name
                mods_dir = item_dir / "mods"
                search_dir = mods_dir if mods_dir.exists() else item_dir
                for root, _, files in os.walk(search_dir):
                    if "mod.info" in files:
                        info_path = Path(root) / "mod.info"
                        discovered.extend(cls.parse_mod_info_file(info_path, workshop_id=workshop_id))
        return discovered

    @classmethod
    def parse_server_ini(cls, ini_path: Path) -> dict:
        """提取现有 ini 配置文件中的 Mods 和 WorkshopItems 列表"""
        res = {"mods": [], "workshop_items": []}
        if not ini_path.exists():
            return res
        
        with open(ini_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Mods="):
                    val = line.split("=", 1)[1]
                    res["mods"] = [m for m in val.split(";") if m]
                elif line.startswith("WorkshopItems="):
                    val = line.split("=", 1)[1]
                    res["workshop_items"] = [w for w in val.split(";") if w]
        return res