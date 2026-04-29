"""
反向归集（Adopt）

把 AI 工具目录下已存在的真实 skill 目录归集到中央仓库，并替换为软链。

流程：
1. 备份原始目录到 backups/<timestamp>/<tool_key>/<skill_name>/
2. 移动原目录到 store/<skill_name>/  （若 store 中已有同名 skill 则跳过/覆盖）
3. 在原位置创建软链 → store/<skill_name>/
4. 写 manifest（source.type = 'adopted'）
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from . import linker, manifest, store
from .config import get_backup_dir
from .tools import (
    detect_skill_dirs,
    expand_path,
    get_skill_version,
    get_tool_config,
    is_valid_skill_dir,
)


# ---------------------------------------------------------------------------
# 扫描
# ---------------------------------------------------------------------------

def scan_existing_skills(only_real: bool = True) -> List[Dict]:
    """
    扫描所有已检测到的 AI 工具目录，列出其中现存的 skill。

    Args:
        only_real: True 表示只返回真实目录（非软链），用于反向归集

    Returns:
        [{tool_key, tool_name, name, path, version, is_symlink, points_to}]
    """
    result = []
    for dir_info in detect_skill_dirs():
        tool_key = dir_info["tool_key"]
        tool_name = dir_info["name"]
        skills_dir = dir_info["path"]

        for item in sorted(skills_dir.iterdir()):
            # 必须是目录或者指向目录的软链
            is_symlink = item.is_symlink()
            try:
                has_skill_md = (item / "SKILL.md").exists()
            except OSError:
                has_skill_md = False
            if not has_skill_md:
                continue

            if only_real and is_symlink:
                continue

            real_path = item.resolve() if is_symlink else item
            result.append({
                "tool_key": tool_key,
                "tool_name": tool_name,
                "name": item.name,
                "path": str(item),
                "version": get_skill_version(real_path),
                "is_symlink": is_symlink,
                "points_to": str(real_path) if is_symlink else None,
            })
    return result


# ---------------------------------------------------------------------------
# 备份
# ---------------------------------------------------------------------------

def _make_backup(skill_path: Path, tool_key: str) -> Path:
    """把 skill 目录拷贝到 backups/<timestamp>/<tool_key>/<name>/"""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = get_backup_dir() / ts / tool_key
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / skill_path.name
    shutil.copytree(str(skill_path), str(dest))
    return dest


# ---------------------------------------------------------------------------
# 单个归集
# ---------------------------------------------------------------------------

def adopt_skill(
    tool_key: str,
    skill_name: str,
    *,
    backup: bool = True,
    overwrite_store: bool = False,
    relink_all: bool = True,
    dry_run: bool = False,
) -> Dict:
    """
    将某 AI 工具目录下的真实 skill 归集到中央仓库。

    Returns:
        {ok, action, note, store_path, backup_path, linked_targets}
    """
    cfg = get_tool_config(tool_key)
    if cfg is None:
        return {"ok": False, "action": "skipped", "note": f"未知 tool_key: {tool_key}"}

    tool_dir = expand_path(cfg["skill_dir"])
    src = tool_dir / skill_name

    if not src.exists():
        return {"ok": False, "action": "skipped", "note": f"源不存在: {src}"}
    if src.is_symlink():
        return {"ok": False, "action": "skipped", "note": "已是软链，无需归集"}
    if not is_valid_skill_dir(src):
        return {"ok": False, "action": "skipped", "note": "不是合法 skill 目录"}

    target_store_path = store.get_skill_path(skill_name)

    if target_store_path.exists() and not overwrite_store:
        return {
            "ok": False,
            "action": "skipped",
            "note": f"中央仓库已存在同名 skill: {target_store_path}（使用 --overwrite 覆盖）",
        }

    if dry_run:
        return {
            "ok": True,
            "action": "would-adopt",
            "note": f"将归集 {src} → {target_store_path}",
            "store_path": str(target_store_path),
            "backup_path": "(dry-run)",
        }

    # 1. 备份
    backup_path = None
    if backup:
        backup_path = _make_backup(src, tool_key)

    # 2. 移到中央仓库
    store.init_store()
    store_path = store.add_skill_from_path(
        src, name=skill_name, overwrite=overwrite_store, move=True
    )
    version = get_skill_version(store_path)

    # 3. 在原位置创建软链
    link_res = linker.create_link(store_path, tool_key, dry_run=False)

    # 4. 可选：链接到所有其他工具
    linked_targets = [tool_key] if link_res.get("ok") else []
    if relink_all:
        all_res = linker.link_to_all(store_path)
        for tk, r in all_res.items():
            if r.get("ok") and tk not in linked_targets:
                linked_targets.append(tk)

    # 5. 写 manifest
    manifest.add_skill_entry(
        name=skill_name,
        version=version,
        source_type="adopted",
        source_ref=f"{tool_key}:{src}",
        linked_targets=linked_targets,
    )

    return {
        "ok": True,
        "action": "adopted",
        "note": f"已归集到 {store_path}，并链接到 {len(linked_targets)} 个工具",
        "store_path": str(store_path),
        "backup_path": str(backup_path) if backup_path else None,
        "linked_targets": linked_targets,
    }


# ---------------------------------------------------------------------------
# 批量归集
# ---------------------------------------------------------------------------

def adopt_all(
    *,
    backup: bool = True,
    overwrite_store: bool = False,
    relink_all: bool = True,
    dry_run: bool = False,
    name_filter: Optional[str] = None,
    tool_filter: Optional[str] = None,
) -> List[Dict]:
    """
    批量归集所有真实 skill 目录。

    冲突处理：
    - 多个工具下存在同名 skill 真实目录时，**第一个**会成功归集，
      后续因中央仓库已存在而 skipped；如果用户开 --overwrite，
      则后者会覆盖前者（一般不推荐，除非你确认它们是同一个 skill）。
    """
    results = []
    candidates = scan_existing_skills(only_real=True)

    for c in candidates:
        if name_filter and c["name"] != name_filter:
            continue
        if tool_filter and c["tool_key"] != tool_filter:
            continue

        res = adopt_skill(
            c["tool_key"],
            c["name"],
            backup=backup,
            overwrite_store=overwrite_store,
            relink_all=relink_all,
            dry_run=dry_run,
        )
        res["tool_key"] = c["tool_key"]
        res["tool_name"] = c["tool_name"]
        res["skill"] = c["name"]
        results.append(res)

    return results
