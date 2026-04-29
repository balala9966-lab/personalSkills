"""
全局配置管理

负责中央仓库的全局配置：
- 仓库根路径（store home）
- 默认目标工具开关
- 用户偏好

环境变量 SKILL_STORE_HOME 可覆盖默认根路径。
"""

import json
import os
from pathlib import Path
from typing import Dict, List

from .tools import expand_path, list_tool_keys


# ---------------------------------------------------------------------------
# 默认值
# ---------------------------------------------------------------------------

DEFAULT_STORE_HOME = "~/.skill-store"
ENV_STORE_HOME = "SKILL_STORE_HOME"

DEFAULT_CONFIG = {
    "version": "2.1",
    "store_home": DEFAULT_STORE_HOME,
    "default_targets": [],   # 空表示自动检测全部
    "auto_link_on_install": True,
    "backup_before_adopt": True,
    # 通用扫描配置（v2.1+）
    "scan": {
        "max_depth": 4,                # 从 ~ 起算的最大深度
        "extra_dir_names": [],         # 默认 {"skills","skill"} 之外要识别的目录名
        "exclude_prefixes": [],        # 在内置 EXCLUDE_PREFIXES 之外追加要排除的首层目录名
        "extra_aliases": {},           # 用户自定义路径→{tool_key,name,project_dir?} 的额外别名
    },
    # 双 scope 支持（v2.1+，借鉴 agent-skills-hub）
    "default_scope": "global",         # global | project；CLI 未传 --scope 时的默认行为
    # 链接策略（v2.1+，跨平台支持）
    "link_strategy": "auto",           # auto | symlink | copy
                                       # auto: macOS/Linux→symlink，Windows→copy
}


# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------

def get_store_home() -> Path:
    """
    获取中央仓库根目录。

    优先级：
    1. 环境变量 SKILL_STORE_HOME
    2. config.json 中的 store_home
    3. DEFAULT_STORE_HOME
    """
    env_value = os.environ.get(ENV_STORE_HOME)
    if env_value:
        return expand_path(env_value)

    cfg_path = expand_path(DEFAULT_STORE_HOME) / "config.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return expand_path(data.get("store_home", DEFAULT_STORE_HOME))
        except (json.JSONDecodeError, IOError):
            pass

    return expand_path(DEFAULT_STORE_HOME)


def get_config_path() -> Path:
    return get_store_home() / "config.json"


def get_store_dir() -> Path:
    return get_store_home() / "store"


def get_manifest_path() -> Path:
    return get_store_home() / "manifest.json"


def get_backup_dir() -> Path:
    return get_store_home() / "backups"


# ---------------------------------------------------------------------------
# 配置读写
# ---------------------------------------------------------------------------

def load_config() -> Dict:
    cfg_path = get_config_path()
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = dict(DEFAULT_CONFIG)
                merged.update(data)
                return merged
        except (json.JSONDecodeError, IOError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: Dict) -> None:
    cfg_path = get_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def set_store_home(new_home: str) -> Dict:
    """更新仓库根路径。仅修改配置，不会自动迁移已有数据。"""
    config = load_config()
    config["store_home"] = new_home
    save_config(config)
    return config


def get_default_targets() -> List[str]:
    config = load_config()
    targets = config.get("default_targets") or []
    if not targets:
        return list_tool_keys()
    return targets


def get_scan_config() -> Dict:
    """
    返回 scan 配置（合并默认值）。

    供 tools.discover_skill_dirs() 使用，避免 tools 与 config 直接强耦合。
    """
    cfg = load_config()
    scan = dict(DEFAULT_CONFIG["scan"])
    user_scan = cfg.get("scan") or {}
    if isinstance(user_scan, dict):
        scan.update(user_scan)
    return scan

def get_default_scope() -> str:
    """返回默认 scope（global / project）；非法值回退到 global"""
    cfg = load_config()
    val = cfg.get("default_scope") or "global"
    if val not in ("global", "project"):
        return "global"
    return val

def get_link_strategy() -> str:
    """返回链接策略（auto / symlink / copy）；非法值回退到 auto"""
    cfg = load_config()
    val = cfg.get("link_strategy") or "auto"
    if val not in ("auto", "symlink", "copy"):
        return "auto"
    return val


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------

def ensure_initialized() -> Path:
    """
    确保中央仓库目录结构存在，返回 store_home。

    创建：
    - {store_home}/
    - {store_home}/store/
    - {store_home}/backups/
    - {store_home}/config.json (若不存在)
    """
    store_home = get_store_home()
    store_home.mkdir(parents=True, exist_ok=True)
    get_store_dir().mkdir(parents=True, exist_ok=True)
    get_backup_dir().mkdir(parents=True, exist_ok=True)

    cfg_path = get_config_path()
    if not cfg_path.exists():
        save_config(DEFAULT_CONFIG)

    return store_home
