"""
软链接 / 目录复制 管理 (v2.1)

负责把中央仓库中的 skill 分发到 AI 工具的 skills 目录。
支持双 scope（global/project）与双 link_type（symlink/copy）。

链接策略决策（_strategy）：
  explicit > config.link_strategy > 平台默认（win → copy，*nix → symlink）
"""

import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .tools import (
    TOOL_CONFIGS, detect_skill_dirs, discover_project_skill_dirs,
    expand_path, get_tool_config, get_tool_dir, get_tool_name,
)

# ---------------------------------------------------------------------------
# 链接类型常量
# ---------------------------------------------------------------------------

LINK_TYPE_SYMLINK = "symlink"
LINK_TYPE_COPY = "copy"
LINK_TYPE_AUTO = "auto"

def _strategy(explicit: str = LINK_TYPE_AUTO) -> str:
    """
    决策实际使用的 link_type。
    explicit > config.link_strategy > 平台默认（win→copy，*nix→symlink）
    """
    if explicit in (LINK_TYPE_SYMLINK, LINK_TYPE_COPY):
        return explicit
    try:
        from . import config
        cfg_val = config.get_link_strategy()
    except Exception:
        cfg_val = LINK_TYPE_AUTO
    if cfg_val in (LINK_TYPE_SYMLINK, LINK_TYPE_COPY):
        return cfg_val
    return LINK_TYPE_COPY if sys.platform == "win32" else LINK_TYPE_SYMLINK

def _tool_skill_dir(tool_key: str, scope: str = "global",
                    cwd: Optional[Path] = None):
    """
    取某 tool_key 在指定 scope 下的 skill_dir 路径。
    优先走 tools.get_tool_dir（统一入口）；未知 tool_key 返回 None。
    """
    return get_tool_dir(tool_key, scope=scope, cwd=cwd)

# ---------------------------------------------------------------------------
# 链接状态
# ---------------------------------------------------------------------------

LINK_STATUS_LINKED = "linked"            # ✅ 软链接 / copy，且指向正确源
LINK_STATUS_OTHER_SOURCE = "other"       # ❌ 软链接，指向其他源
LINK_STATUS_REAL_DIR = "real"            # ⚠️ 真实目录（非软链且非 copy 形态）
LINK_STATUS_NOT_LINKED = "none"          # - 未链接
LINK_STATUS_TOOL_MISSING = "missing"     # · 工具未安装


def _is_skill_dir_copy(target: Path, skill_path: Path) -> bool:
    """
    判断 target 是否是 skill_path 的"目录复制"形态。

    判定条件：
    - target 是真实目录（非符号链接）
    - target 与 skill_path 同名（外层已保证，但再校验一次）
    - target 至少包含 SKILL.md（与源一致）

    注意：内容是否完全相同不验证（成本高且复制后可能被修改），
    本函数只做"看起来像 copy 出来的 skill"的弱校验。
    """
    try:
        if target.is_symlink() or not target.is_dir():
            return False
    except OSError:
        return False
    if target.name != skill_path.name:
        return False
    return (target / "SKILL.md").exists()

def get_link_status(skill_path: Path, tool_key: str, *,
                    scope: str = "global",
                    cwd: Optional[Path] = None) -> Dict:
    """
    检查某 skill 在指定工具+scope 下的链接状态。

    Returns:
        {status, note, target_path, link_type, scope}
        link_type ∈ {"symlink", "copy", ""} （未链接时为 ""）
    """
    tool_dir = _tool_skill_dir(tool_key, scope=scope, cwd=cwd)
    if tool_dir is None:
        return {
            "status": LINK_STATUS_TOOL_MISSING,
            "note": f"未知 tool_key 或不支持 scope={scope}: {tool_key}",
            "target_path": "",
            "link_type": "",
            "scope": scope,
        }
    if not tool_dir.exists():
        return {
            "status": LINK_STATUS_TOOL_MISSING,
            "note": "工具/项目级目录未创建",
            "target_path": str(tool_dir),
            "link_type": "",
            "scope": scope,
        }

    target = tool_dir / skill_path.name
    if target.is_symlink():
        try:
            existing = target.resolve()
        except OSError:
            existing = None
        if existing == skill_path.resolve():
            return {
                "status": LINK_STATUS_LINKED, "note": "已链接",
                "target_path": str(target),
                "link_type": LINK_TYPE_SYMLINK, "scope": scope,
            }
        return {
            "status": LINK_STATUS_OTHER_SOURCE,
            "note": f"指向: {existing}",
            "target_path": str(target),
            "link_type": LINK_TYPE_SYMLINK, "scope": scope,
        }
    if target.exists():
        # 真实目录：可能是 copy 形态（v2.1 支持），也可能是用户自建的
        if _is_skill_dir_copy(target, skill_path):
            return {
                "status": LINK_STATUS_LINKED, "note": "已复制（copy）",
                "target_path": str(target),
                "link_type": LINK_TYPE_COPY, "scope": scope,
            }
        return {
            "status": LINK_STATUS_REAL_DIR, "note": "真实目录",
            "target_path": str(target),
            "link_type": "", "scope": scope,
        }
    return {
        "status": LINK_STATUS_NOT_LINKED, "note": "未链接",
        "target_path": str(target),
        "link_type": "", "scope": scope,
    }


# ---------------------------------------------------------------------------
# 创建/删除链接（v2.1: 支持 scope/cwd/link_type）
# ---------------------------------------------------------------------------

def create_link(
    skill_path: Path,
    tool_key: str,
    *,
    scope: str = "global",
    cwd: Optional[Path] = None,
    link_type: str = LINK_TYPE_AUTO,
    create_parent: bool = True,
    overwrite_other_source: bool = True,
    dry_run: bool = False,
) -> Dict:
    """
    在指定工具+scope 下为 skill 创建软链接或目录复制。

    Args:
        scope:     'global' | 'project'
        cwd:       project 模式下的项目根（默认 Path.cwd()）
        link_type: 'auto' | 'symlink' | 'copy'

    Returns:
        {ok, action, note, link_type, scope, target_path}
        action ∈ {"created", "kept", "replaced", "skipped", "would-create"}
    """
    tool_dir = _tool_skill_dir(tool_key, scope=scope, cwd=cwd)
    if tool_dir is None:
        return {
            "ok": False, "action": "skipped",
            "note": f"未知 tool_key 或不支持 scope={scope}: {tool_key}",
            "link_type": "", "scope": scope, "target_path": "",
        }

    actual_link_type = _strategy(link_type)
    target = tool_dir / skill_path.name

    if not tool_dir.exists():
        if not create_parent:
            return {
                "ok": False, "action": "skipped", "note": "tool dir 不存在",
                "link_type": actual_link_type, "scope": scope,
                "target_path": str(target),
            }
        if dry_run:
            return {
                "ok": True, "action": "would-create",
                "note": f"将创建目录 {tool_dir} 并建立 {actual_link_type}",
                "link_type": actual_link_type, "scope": scope,
                "target_path": str(target),
            }
        tool_dir.mkdir(parents=True, exist_ok=True)

    # 处理已存在的 target
    if target.is_symlink():
        try:
            existing = target.resolve()
        except OSError:
            existing = None
        if existing == skill_path.resolve() and actual_link_type == LINK_TYPE_SYMLINK:
            return {
                "ok": True, "action": "kept", "note": "已正确链接",
                "link_type": LINK_TYPE_SYMLINK, "scope": scope,
                "target_path": str(target),
            }
        if not overwrite_other_source:
            return {
                "ok": False, "action": "skipped",
                "note": f"已链接到其他源: {existing}",
                "link_type": LINK_TYPE_SYMLINK, "scope": scope,
                "target_path": str(target),
            }
        if dry_run:
            return {
                "ok": True, "action": "would-create",
                "note": f"将替换软链为 {actual_link_type} → {skill_path}",
                "link_type": actual_link_type, "scope": scope,
                "target_path": str(target),
            }
        target.unlink()
    elif target.exists():
        # 真实目录：copy 形态可视为"已存在"，幂等保留
        if actual_link_type == LINK_TYPE_COPY and _is_skill_dir_copy(target, skill_path):
            return {
                "ok": True, "action": "kept", "note": "已复制（保留）",
                "link_type": LINK_TYPE_COPY, "scope": scope,
                "target_path": str(target),
            }
        return {
            "ok": False, "action": "skipped",
            "note": "目标是真实目录，请用 adopt 归集或先删除",
            "link_type": "", "scope": scope, "target_path": str(target),
        }

    if dry_run:
        return {
            "ok": True, "action": "would-create",
            "note": f"将创建 {actual_link_type} → {skill_path}",
            "link_type": actual_link_type, "scope": scope,
            "target_path": str(target),
        }

    # 实际创建
    try:
        if actual_link_type == LINK_TYPE_COPY:
            shutil.copytree(str(skill_path), str(target), symlinks=False)
            note = f"已复制 → {skill_path}"
        else:
            target.symlink_to(skill_path)
            note = f"已链接 → {skill_path}"
        return {
            "ok": True, "action": "created", "note": note,
            "link_type": actual_link_type, "scope": scope,
            "target_path": str(target),
        }
    except OSError as e:
        # 软链失败时（如 Windows 普通用户）自动降级到 copy
        if actual_link_type == LINK_TYPE_SYMLINK:
            try:
                shutil.copytree(str(skill_path), str(target), symlinks=False)
                return {
                    "ok": True, "action": "created",
                    "note": f"软链失败({e})，已自动降级为复制 → {skill_path}",
                    "link_type": LINK_TYPE_COPY, "scope": scope,
                    "target_path": str(target),
                }
            except OSError as e2:
                return {
                    "ok": False, "action": "skipped",
                    "note": f"创建失败（含降级）: {e2}",
                    "link_type": "", "scope": scope, "target_path": str(target),
                }
        return {
            "ok": False, "action": "skipped", "note": f"创建失败: {e}",
            "link_type": "", "scope": scope, "target_path": str(target),
        }

def remove_link(skill_path: Path, tool_key: str, *,
                scope: str = "global",
                cwd: Optional[Path] = None,
                dry_run: bool = False) -> Dict:
    """
    删除指定工具+scope 下的链接（软链或 copy 目录）。

    自动识别 link_type：
    - 软链且指向当前 skill_path → 删除
    - 真实目录且看起来是 copy 出来的（同名 + 含 SKILL.md）→ rmtree 删除
    - 否则保护性跳过
    """
    tool_dir = _tool_skill_dir(tool_key, scope=scope, cwd=cwd)
    if tool_dir is None:
        return {
            "ok": False, "action": "skipped",
            "note": f"未知 tool_key 或不支持 scope={scope}: {tool_key}",
            "link_type": "", "scope": scope, "target_path": "",
        }
    target = tool_dir / skill_path.name

    if not target.exists() and not target.is_symlink():
        return {
            "ok": True, "action": "kept", "note": "未链接",
            "link_type": "", "scope": scope, "target_path": str(target),
        }

    if target.is_symlink():
        try:
            existing = target.resolve()
        except OSError:
            existing = None
        if existing != skill_path.resolve():
            return {
                "ok": False, "action": "skipped",
                "note": f"软链指向其他源: {existing}",
                "link_type": LINK_TYPE_SYMLINK, "scope": scope,
                "target_path": str(target),
            }
        if dry_run:
            return {
                "ok": True, "action": "would-remove", "note": "将删除软链",
                "link_type": LINK_TYPE_SYMLINK, "scope": scope,
                "target_path": str(target),
            }
        target.unlink()
        return {
            "ok": True, "action": "removed", "note": "已删除软链",
            "link_type": LINK_TYPE_SYMLINK, "scope": scope,
            "target_path": str(target),
        }

    # 真实目录：仅当看起来像 copy 形态时才允许删除
    if _is_skill_dir_copy(target, skill_path):
        if dry_run:
            return {
                "ok": True, "action": "would-remove",
                "note": "将删除复制目录",
                "link_type": LINK_TYPE_COPY, "scope": scope,
                "target_path": str(target),
            }
        try:
            shutil.rmtree(str(target))
            return {
                "ok": True, "action": "removed", "note": "已删除复制目录",
                "link_type": LINK_TYPE_COPY, "scope": scope,
                "target_path": str(target),
            }
        except OSError as e:
            return {
                "ok": False, "action": "skipped", "note": f"删除失败: {e}",
                "link_type": LINK_TYPE_COPY, "scope": scope,
                "target_path": str(target),
            }

    return {
        "ok": False, "action": "skipped",
        "note": "目标是真实目录（非 copy 形态），跳过",
        "link_type": "", "scope": scope, "target_path": str(target),
    }

# ---------------------------------------------------------------------------
# 批量操作
# ---------------------------------------------------------------------------

def _resolve_targets_for_scope(targets: Optional[List[str]],
                                scope: str,
                                cwd: Optional[Path]) -> List[str]:
    """
    根据 scope 决定默认 targets：
    - global:  detect_skill_dirs() 检测到的工具
    - project: discover_project_skill_dirs(cwd) 中已存在的；
               若无则取所有别名表中带 project_dir 的工具
    """
    if targets is not None:
        return list(targets)
    if scope == "project":
        existing = [d["tool_key"] for d in discover_project_skill_dirs(cwd)]
        if existing:
            return existing
        from .tools import KNOWN_TOOL_ALIASES
        return [info["tool_key"] for info in KNOWN_TOOL_ALIASES.values()
                if info.get("project_dir")]
    return [d["tool_key"] for d in detect_skill_dirs()]

def link_to_all(
    skill_path: Path,
    *,
    targets: Optional[List[str]] = None,
    scope: str = "global",
    cwd: Optional[Path] = None,
    link_type: str = LINK_TYPE_AUTO,
    dry_run: bool = False,
) -> Dict[str, Dict]:
    """
    将 skill 链接到所有指定 / 检测到的工具目录。

    Args:
        targets:   指定 tool_key 列表；None 时根据 scope 自动决定
        scope:     'global' | 'project'
        cwd:       project 模式下的项目根
        link_type: 'auto' | 'symlink' | 'copy'

    Returns:
        {tool_key: {ok, action, note, link_type, scope, target_path}}
    """
    targets = _resolve_targets_for_scope(targets, scope, cwd)

    results: Dict[str, Dict] = {}
    for tk in targets:
        if scope == "global" and get_tool_config(tk) is None:
            results[tk] = {
                "ok": False, "action": "skipped", "note": "未知 tool_key",
                "link_type": "", "scope": scope, "target_path": "",
            }
            continue
        results[tk] = create_link(
            skill_path, tk, scope=scope, cwd=cwd,
            link_type=link_type, dry_run=dry_run,
        )
    return results

def unlink_from_all(
    skill_path: Path,
    *,
    targets: Optional[List[str]] = None,
    scope: str = "global",
    cwd: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Dict]:
    """从所有指定 / 检测到的工具中移除软链 / copy 目录"""
    targets = _resolve_targets_for_scope(targets, scope, cwd)
    results: Dict[str, Dict] = {}
    for tk in targets:
        if scope == "global" and get_tool_config(tk) is None:
            results[tk] = {
                "ok": False, "action": "skipped", "note": "未知 tool_key",
                "link_type": "", "scope": scope, "target_path": "",
            }
            continue
        results[tk] = remove_link(
            skill_path, tk, scope=scope, cwd=cwd, dry_run=dry_run,
        )
    return results

def get_currently_linked_targets(skill_path: Path, *,
                                  scope: str = "global",
                                  cwd: Optional[Path] = None) -> List[Dict]:
    """
    返回当前真正链接到该 skill_path 的目标列表（v2.1 形态）。

    Returns:
        [{tool_key, scope, link_type, project_root?}]
    """
    linked: List[Dict] = []

    def _scan(sc: str, c: Optional[Path]):
        if sc == "global":
            tk_list = [d["tool_key"] for d in detect_skill_dirs()]
        else:
            tk_list = [d["tool_key"] for d in discover_project_skill_dirs(c)]
        for tk in tk_list:
            st = get_link_status(skill_path, tk, scope=sc, cwd=c)
            if st["status"] == LINK_STATUS_LINKED:
                entry = {"tool_key": tk, "scope": sc,
                         "link_type": st.get("link_type", LINK_TYPE_SYMLINK)}
                if sc == "project" and c is not None:
                    try:
                        entry["project_root"] = str(Path(c).resolve())
                    except OSError:
                        entry["project_root"] = str(c)
                linked.append(entry)

    if scope == "all":
        _scan("global", None)
        _scan("project", cwd)
    else:
        _scan(scope, cwd)
    return linked
