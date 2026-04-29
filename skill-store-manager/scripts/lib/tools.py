"""
AI 工具检测与配置模块（通用扫描版）

不再依赖硬编码白名单，而是扫描 ~/ 下的隐藏目录寻找符合
"AI 工具 skills 目录" 结构的位置；已知工具保留为友好名别名表。

判定规则：
- 范围：~/ 下首层以 . 开头的隐藏目录
- 深度：从 ~ 起算 ≤ 4 层
- 目录名：skills 或 skill（可通过 config 扩展）
- 命中：目录内至少有一个子目录含 SKILL.md（include_empty=True 可放宽）
- 排除：.git/.Trash/.cache/.npm/.node_modules/.vscode/.idea/.docker/.Steam/.Spotify/.ssh/.gnupg 等
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# 已知工具友好名别名表（路径 → {tool_key, name}）
# 命中后显示官方友好名，否则按路径推断
# ---------------------------------------------------------------------------

KNOWN_TOOL_ALIASES: Dict[str, Dict[str, Optional[str]]] = {
    "~/.claude/skills":                  {"tool_key": "claude-code",   "name": "Claude Code",        "project_dir": ".claude/skills"},
    "~/.codex/skills":                   {"tool_key": "codex-cli",     "name": "Codex CLI (OpenAI)", "project_dir": ".codex/skills"},
    "~/.codefuse/engine/codex/skills":   {"tool_key": "codex-engine",  "name": "Codex Engine",       "project_dir": None},
    "~/.codefuse/engine/cc/skills":      {"tool_key": "codefuse",      "name": "CodeFuse",           "project_dir": ".codefuse/skills"},
    "~/.codefuse/fuse/skills":           {"tool_key": "codefuse-fuse", "name": "CodeFuse (Fuse)",    "project_dir": None},
    "~/.codeium/windsurf/skills":        {"tool_key": "windsurf",      "name": "Windsurf",           "project_dir": ".windsurf/skills"},
    "~/.openclaw/workspace/skills":      {"tool_key": "openclaw",      "name": "OpenClaw",           "project_dir": ".openclaw/skills"},
    "~/.opencode/skills":                {"tool_key": "opencode",      "name": "OpenCode",           "project_dir": ".opencode/skill"},
    "~/.homiclaw/workspace/user-skills": {"tool_key": "homiclaw",      "name": "Homiclaw",           "project_dir": None},
    "~/.homiclaw/workspace/skills":      {"tool_key": "homiclaw-ws",   "name": "Homiclaw Workspace", "project_dir": None},
    "~/.agents/skills":                  {"tool_key": "agents",        "name": "Agents",             "project_dir": ".agents/skills"},
    "~/.cursor/skills":                  {"tool_key": "cursor",        "name": "Cursor",             "project_dir": ".cursor/skills"},
}

# 默认目录名匹配（支持复数/单数）
DEFAULT_DIR_NAMES: Set[str] = {"skills", "skill"}

# 默认排除前缀（首层目录名匹配则整树跳过）
EXCLUDE_PREFIXES: Set[str] = {
    ".git", ".Trash", ".trash", ".cache", ".npm", ".pnpm-store", ".yarn",
    ".node_modules", ".vscode", ".idea", ".docker", ".Steam", ".Spotify",
    ".ssh", ".gnupg", ".m2", ".gradle", ".rustup", ".cargo",
    ".CFUserTextEncoding", ".DS_Store", ".local",
}

# 模块级缓存（同一进程内复用扫描结果）
_DISCOVERY_CACHE: Optional[List[Dict]] = None

# ---------------------------------------------------------------------------
# 路径工具
# ---------------------------------------------------------------------------

def expand_path(path: str) -> Path:
    """展开路径中的 ~ 和环境变量"""
    return Path(os.path.expanduser(os.path.expandvars(path)))

# ---------------------------------------------------------------------------
# 别名/推断
# ---------------------------------------------------------------------------

def _build_alias_index() -> Dict[Path, Dict[str, str]]:
    """构建以展开后的绝对路径为 key 的别名表（含 config 中的 extra_aliases）"""
    index: Dict[Path, Dict[str, str]] = {}
    for raw_path, info in KNOWN_TOOL_ALIASES.items():
        try:
            index[expand_path(raw_path).resolve()] = dict(info)
        except OSError:
            index[expand_path(raw_path)] = dict(info)
    try:
        from . import config as _cfg
        scan_cfg = _cfg.get_scan_config()
        for raw_path, info in (scan_cfg.get("extra_aliases") or {}).items():
            try:
                index[expand_path(raw_path).resolve()] = dict(info)
            except Exception:
                pass
    except Exception:
        pass
    return index


def _infer_tool_info(skills_dir: Path, home: Path) -> Dict[str, str]:
    """
    路径推断 tool_key 与友好名。

    - tool_key: home 之后到 skills 之间的路径段，去掉首层 . 前缀，用 - 拼接
      ~/.foo/skills              → foo
      ~/.codefuse/engine/cc/skills → codefuse-engine-cc
    - name: tool_key 的首字母大写、- 替换为空格
    """
    try:
        rel = skills_dir.relative_to(home)
    except ValueError:
        fallback = skills_dir.parent.name.lstrip(".")
        return {"tool_key": fallback or "unknown",
                "name": (fallback or "Unknown").title()}

    parts = list(rel.parts)
    if parts and parts[-1] in DEFAULT_DIR_NAMES:
        parts = parts[:-1]
    if not parts:
        return {"tool_key": "home", "name": "Home"}

    parts[0] = parts[0].lstrip(".")
    tool_key = "-".join(p for p in parts if p)
    name = " ".join(p.capitalize() for p in tool_key.split("-"))
    return {"tool_key": tool_key, "name": name}


def _resolve_tool_info(skills_dir: Path, home: Path,
                       alias_index: Dict[Path, Dict[str, str]]) -> Dict[str, str]:
    """优先查别名表，未命中则推断"""
    try:
        key = skills_dir.resolve()
    except OSError:
        key = skills_dir
    hit = alias_index.get(key)
    if hit:
        return dict(hit)
    return _infer_tool_info(skills_dir, home)

# ---------------------------------------------------------------------------
# 核心：扫描发现 skills 目录
# ---------------------------------------------------------------------------

def _has_skill_md_child(d: Path) -> bool:
    """判断目录内是否至少有一个子目录包含 SKILL.md"""
    try:
        for child in d.iterdir():
            try:
                if child.is_symlink():
                    real = child.resolve()
                    if real.is_dir() and (real / "SKILL.md").exists():
                        return True
                elif child.is_dir():
                    if (child / "SKILL.md").exists():
                        return True
            except OSError:
                continue
    except OSError:
        return False
    return False


def _scan_for_skills_dirs(start: Path, dir_names: Set[str], exclude_prefixes: Set[str],
                          remaining_depth: int, visited: Set[Path]) -> List[Path]:
    """
    深度优先扫描：找出所有名字匹配 dir_names 的目录。

    Args:
        remaining_depth: 从 start 起还能向下递归的层数（0 表示不再深入）
        visited: 已访问的真实路径集合（防符号链接环）
    """
    found: List[Path] = []
    try:
        real = start.resolve()
    except OSError:
        return found
    if real in visited:
        return found
    visited.add(real)

    if start.name in dir_names:
        try:
            if start.is_dir():
                found.append(start)
        except OSError:
            pass
        return found  # 命中后不再深入

    if remaining_depth <= 0:
        return found

    try:
        entries = list(start.iterdir())
    except OSError:
        return found

    for entry in entries:
        try:
            if not entry.is_dir():
                continue
        except OSError:
            continue
        if entry.name in exclude_prefixes:
            continue
        found.extend(_scan_for_skills_dirs(
            entry, dir_names, exclude_prefixes, remaining_depth - 1, visited
        ))
    return found


def discover_skill_dirs(home: Optional[Path] = None,
                        max_depth: int = 4,
                        include_empty: bool = True,
                        refresh: bool = False,
                        scope: str = "global",
                        cwd: Optional[Path] = None) -> List[Dict]:
    """
    通用扫描：发现本机所有 AI 工具的 skills 目录。

    Args:
        scope: 'global' 扫 ~/，'project' 扫 cwd 下的 .xxx/skills，'all' 合并
        cwd:   project / all 模式下的项目根，默认 Path.cwd()

    Returns:
        [{tool_key, name, path: Path, alias: bool, has_skills: bool, scope: str}]
    """
    if scope == "project":
        return discover_project_skill_dirs(cwd)
    if scope == "all":
        global_results = discover_skill_dirs(
            home=home, max_depth=max_depth, include_empty=include_empty,
            refresh=refresh, scope="global", cwd=None,
        )
        project_results = discover_project_skill_dirs(cwd)
        return list(global_results) + list(project_results)

    global _DISCOVERY_CACHE

    using_default_home = home is None
    if using_default_home and not refresh and _DISCOVERY_CACHE is not None:
        return list(_DISCOVERY_CACHE)

    if home is None:
        home = Path.home()
    try:
        home = home.resolve()
    except OSError:
        pass

    dir_names = set(DEFAULT_DIR_NAMES)
    exclude_prefixes = set(EXCLUDE_PREFIXES)
    try:
        from . import config as _cfg
        scan_cfg = _cfg.get_scan_config()
        cfg_depth = scan_cfg.get("max_depth")
        if cfg_depth:
            max_depth = int(cfg_depth)
        for n in (scan_cfg.get("extra_dir_names") or []):
            dir_names.add(n)
        for n in (scan_cfg.get("exclude_prefixes") or []):
            exclude_prefixes.add(n)
    except Exception:
        pass

    alias_index = _build_alias_index()
    candidates: List[Path] = []
    seen_paths: Set[Path] = set()

    # 1) 别名表预设路径优先
    for raw_path in KNOWN_TOOL_ALIASES:
        p = expand_path(raw_path)
        if not p.exists():
            continue
        try:
            rp = p.resolve()
        except OSError:
            rp = p
        if rp not in seen_paths:
            seen_paths.add(rp)
            candidates.append(p)

    # 2) 扫描 ~/ 下首层隐藏目录
    visited: Set[Path] = set()
    try:
        first_level = list(home.iterdir())
    except OSError:
        first_level = []

    for entry in first_level:
        if not entry.name.startswith("."):
            continue
        if entry.name in exclude_prefixes:
            continue
        try:
            if not entry.is_dir():
                continue
        except OSError:
            continue
        for found in _scan_for_skills_dirs(
            entry, dir_names, exclude_prefixes, max_depth - 1, visited
        ):
            try:
                rp = found.resolve()
            except OSError:
                rp = found
            if rp not in seen_paths:
                seen_paths.add(rp)
                candidates.append(found)

    # 3) 过滤 + 推断
    raw_results: List[Dict] = []
    for skills_dir in candidates:
        try:
            rp = skills_dir.resolve()
        except OSError:
            rp = skills_dir
        is_alias = rp in alias_index
        has_skills = _has_skill_md_child(skills_dir)
        if not is_alias and not has_skills and not include_empty:
            continue
        info = _resolve_tool_info(skills_dir, home, alias_index)
        raw_results.append({
            "tool_key": info["tool_key"],
            "name": info["name"],
            "path": skills_dir,
            "alias": is_alias,
            "has_skills": has_skills,
        })

    # 4) 按 tool_key 去重 + 别名优先
    deduped: List[Dict] = []
    seen_keys: Set[str] = set()
    for r in raw_results:
        if r["alias"] and r["tool_key"] not in seen_keys:
            seen_keys.add(r["tool_key"])
            deduped.append(r)
    for r in raw_results:
        if r["tool_key"] in seen_keys:
            continue
        seen_keys.add(r["tool_key"])
        deduped.append(r)

    deduped.sort(key=lambda x: (not x["alias"], x["tool_key"]))

    # 给每条加 scope 字段（global 模式默认 global）
    for item in deduped:
        item.setdefault("scope", "global")

    if using_default_home:
        _DISCOVERY_CACHE = list(deduped)
    return deduped


def clear_discovery_cache() -> None:
    """清空模块级扫描缓存（用于 refresh / 测试）"""
    global _DISCOVERY_CACHE
    _DISCOVERY_CACHE = None

# ---------------------------------------------------------------------------
# 工具目录检测（兼容旧 API）
# ---------------------------------------------------------------------------

def detect_skill_dirs(create_if_parent_exists: bool = False) -> List[Dict]:
    """
    检测本机所有存在的 skills 目录（兼容旧 API）。

    内部转调 discover_skill_dirs。create_if_parent_exists 仅对别名表中
    路径生效（其他工具按扫描结果，已存在才会被发现）。

    Returns:
        列表，每项 {tool_key, name, path: Path}
    """
    detected = discover_skill_dirs(include_empty=True)

    if create_if_parent_exists:
        existing_keys = {d["tool_key"] for d in detected}
        added = False
        for raw_path, info in KNOWN_TOOL_ALIASES.items():
            if info["tool_key"] in existing_keys:
                continue
            skill_dir = expand_path(raw_path)
            if skill_dir.exists():
                continue
            if skill_dir.parent.exists():
                try:
                    skill_dir.mkdir(parents=True, exist_ok=True)
                    detected.append({
                        "tool_key": info["tool_key"],
                        "name": info["name"],
                        "path": skill_dir,
                        "alias": True,
                        "has_skills": False,
                    })
                    added = True
                except OSError:
                    pass
        if added:
            clear_discovery_cache()

    return [{"tool_key": d["tool_key"], "name": d["name"], "path": d["path"]} for d in detected]


def get_tool_config(tool_key: str) -> Optional[Dict]:
    """
    获取指定工具的配置 {name, skill_dir}（兼容旧 API）。

    在 discover 结果里查找；未命中时尝试在别名表中查找；都未命中返回 None。
    """
    for d in discover_skill_dirs():
        if d["tool_key"] == tool_key:
            return {"name": d["name"], "skill_dir": str(d["path"])}
    for raw_path, info in KNOWN_TOOL_ALIASES.items():
        if info["tool_key"] == tool_key:
            return {"name": info["name"], "skill_dir": raw_path}
    return None


def list_tool_keys() -> List[str]:
    """返回当前所有已检测到的工具 key"""
    return [d["tool_key"] for d in discover_skill_dirs()]


def get_tool_name(tool_key: str) -> str:
    """安全获取友好名；未知 tool_key 时退化为 tool_key 本身"""
    cfg = get_tool_config(tool_key)
    return cfg["name"] if cfg else tool_key


# ---------------------------------------------------------------------------
# 向后兼容：TOOL_CONFIGS 改为只读视图
# ---------------------------------------------------------------------------

class _ToolConfigsView:
    """只读视图，访问 TOOL_CONFIGS[tk] 时实时查 discover 结果"""

    def __getitem__(self, tool_key: str) -> Dict:
        cfg = get_tool_config(tool_key)
        if cfg is None:
            raise KeyError(tool_key)
        return cfg

    def __contains__(self, tool_key: str) -> bool:
        return get_tool_config(tool_key) is not None

    def __iter__(self):
        return iter(list_tool_keys())

    def keys(self):
        return list_tool_keys()

    def items(self):
        return [(d["tool_key"], {"name": d["name"], "skill_dir": str(d["path"])})
                for d in discover_skill_dirs()]

    def values(self):
        return [{"name": d["name"], "skill_dir": str(d["path"])}
                for d in discover_skill_dirs()]

    def get(self, tool_key: str, default=None):
        cfg = get_tool_config(tool_key)
        return cfg if cfg is not None else default

    def __len__(self):
        return len(list_tool_keys())


TOOL_CONFIGS = _ToolConfigsView()

# ---------------------------------------------------------------------------
# Skill 元信息
# ---------------------------------------------------------------------------

def get_skill_version(skill_path: Path) -> str:
    """从 package.json 读取 skill 版本号，没有则返回 '未知'"""
    pkg_file = skill_path / "package.json"
    if pkg_file.exists():
        try:
            with open(pkg_file, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
                return pkg_data.get("version", "未知")
        except (json.JSONDecodeError, IOError):
            pass
    return "未知"


def is_valid_skill_dir(path: Path) -> bool:
    """判断一个目录是否是合法的 skill 目录（包含 SKILL.md）"""
    return path.is_dir() and (path / "SKILL.md").exists()

# ---------------------------------------------------------------------------
# 双 scope 支持（v2.1+）
# ---------------------------------------------------------------------------

VALID_SCOPES = ("global", "project", "all")

def _project_dir_for_alias(tool_key: str) -> Optional[str]:
    """从别名表查 tool_key 对应的项目级相对路径（无则 None）"""
    for _, info in KNOWN_TOOL_ALIASES.items():
        if info.get("tool_key") == tool_key:
            return info.get("project_dir")
    # 兜底：从配置 extra_aliases 查
    try:
        from . import config as _cfg
        scan_cfg = _cfg.get_scan_config()
        for _, info in (scan_cfg.get("extra_aliases") or {}).items():
            if info.get("tool_key") == tool_key:
                return info.get("project_dir")
    except Exception:
        pass
    return None

def get_tool_dir(tool_key: str, scope: str = "global",
                 cwd: Optional[Path] = None) -> Optional[Path]:
    """
    统一入口：取某 tool_key 在指定 scope 下的 skills 目录。

    - scope='global' → 别名表 / discover 结果中的 ~/.xxx/skills
    - scope='project' → <cwd>/<project_dir>；project_dir 未配置时返回 None

    返回的路径不保证存在（由调用方决定是否 mkdir）。
    """
    if scope not in ("global", "project"):
        raise ValueError(f"Invalid scope: {scope!r} (expected 'global' or 'project')")

    if scope == "global":
        cfg = get_tool_config(tool_key)
        if cfg:
            return expand_path(cfg["skill_dir"])
        return None

    # scope == 'project'
    proj_rel = _project_dir_for_alias(tool_key)
    if not proj_rel:
        return None
    base = Path(cwd) if cwd is not None else Path.cwd()
    return base / proj_rel

def discover_project_skill_dirs(cwd: Optional[Path] = None) -> List[Dict]:
    """
    扫描 <cwd> 下所有项目级 skills 目录（基于别名表的 project_dir）。

    Returns:
        [{tool_key, name, path, alias=True, has_skills, scope='project'}]
    只返回已存在的目录；未配置 project_dir 的工具自动跳过。
    """
    base = Path(cwd) if cwd is not None else Path.cwd()
    try:
        base = base.resolve()
    except OSError:
        pass

    results: List[Dict] = []
    seen_keys: Set[str] = set()

    for _, info in KNOWN_TOOL_ALIASES.items():
        proj_rel = info.get("project_dir")
        if not proj_rel:
            continue
        tk = info["tool_key"]
        if tk in seen_keys:
            continue
        path = base / proj_rel
        if not path.exists():
            continue
        try:
            if not path.is_dir():
                continue
        except OSError:
            continue
        seen_keys.add(tk)
        results.append({
            "tool_key": tk,
            "name": info["name"],
            "path": path,
            "alias": True,
            "has_skills": _has_skill_md_child(path),
            "scope": "project",
        })

    # 用户自定义别名也支持
    try:
        from . import config as _cfg
        scan_cfg = _cfg.get_scan_config()
        for _, info in (scan_cfg.get("extra_aliases") or {}).items():
            proj_rel = info.get("project_dir")
            if not proj_rel:
                continue
            tk = info.get("tool_key")
            if not tk or tk in seen_keys:
                continue
            path = base / proj_rel
            if not path.exists() or not path.is_dir():
                continue
            seen_keys.add(tk)
            results.append({
                "tool_key": tk,
                "name": info.get("name", tk),
                "path": path,
                "alias": True,
                "has_skills": _has_skill_md_child(path),
                "scope": "project",
            })
    except Exception:
        pass

    results.sort(key=lambda x: x["tool_key"])
    return results
