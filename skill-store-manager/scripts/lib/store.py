"""
中央仓库管理

负责中央仓库目录中 skill 实体的物理存放（add/remove/list/get_path）。
不涉及软链接（linker 模块负责）和元数据（manifest 模块负责）。
"""

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from .config import ensure_initialized, get_store_dir
from .tools import get_skill_version, is_valid_skill_dir


def init_store() -> Path:
    """初始化中央仓库目录结构，返回 store_home"""
    return ensure_initialized()


def get_skill_path(name: str) -> Path:
    """返回中央仓库中某个 skill 应在的路径（不保证存在）"""
    return get_store_dir() / name


def has_skill(name: str) -> bool:
    """中央仓库中是否已存在该 skill"""
    return is_valid_skill_dir(get_skill_path(name))


def list_store_skills() -> List[Dict]:
    """
    列出中央仓库中所有合法 skill。

    Returns:
        [{name, version, path}]
    """
    init_store()
    store_dir = get_store_dir()
    result = []
    for item in sorted(store_dir.iterdir()):
        if is_valid_skill_dir(item):
            result.append({
                "name": item.name,
                "version": get_skill_version(item),
                "path": str(item),
            })
    return result


def add_skill_from_path(
    source: Path,
    name: Optional[str] = None,
    overwrite: bool = False,
    move: bool = False,
) -> Path:
    """
    将本地 skill 目录加入中央仓库。

    Args:
        source: 源 skill 目录（包含 SKILL.md）
        name:   目标名称，默认使用源目录名
        overwrite: 目标已存在时是否覆盖
        move:   True 表示移动（用于 adopt 反向归集），False 表示拷贝

    Returns:
        中央仓库中的目标路径
    """
    init_store()
    if not is_valid_skill_dir(source):
        raise ValueError(f"Not a valid skill dir (no SKILL.md): {source}")

    target_name = name or source.name
    target = get_skill_path(target_name)

    if target.exists():
        if not overwrite:
            raise FileExistsError(f"Skill already exists in store: {target}")
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)

    if move:
        shutil.move(str(source), str(target))
    else:
        shutil.copytree(str(source), str(target))

    return target


def remove_skill(name: str) -> bool:
    """从中央仓库删除 skill 实体目录"""
    target = get_skill_path(name)
    if not target.exists():
        return False
    if target.is_symlink() or target.is_file():
        target.unlink()
    else:
        shutil.rmtree(target)
    return True
