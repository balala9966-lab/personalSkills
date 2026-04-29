#!/usr/bin/env python3
"""
Skill Debug Sync - 自动将 skill 同步到所有已安装的 AI 编程工具

功能：
1. 自动检测本机存在的 AI 编程工具 skills 目录
2. 识别当前正在调试的 skill 目录
3. 创建软连接到所有已安装工具的 skill 目录

Usage:
    sync_skill.py [skill_path] [--dry-run] [--unlink]
    sync_skill.py --skill <name>                    # 按名称查找并同步
    sync_skill.py --detect-dirs                     # 检测本机 skills 目录
    sync_skill.py --list-skills                     # 列出所有检测到的 skill

Examples:
    sync_skill.py                           # 自动检测当前目录的 skill
    sync_skill.py /path/to/my-skill         # 指定 skill 目录
    sync_skill.py --skill my-skill          # 按名称查找并同步
    sync_skill.py --dry-run                 # 只显示会做什么，不实际执行
    sync_skill.py --unlink                  # 删除已存在的软连接
    sync_skill.py --detect-dirs             # 检测本机 skills 目录
    sync_skill.py --list-skills             # 列出所有检测到的 skill
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict


# 已知的 AI 编程工具及其 skill 目录配置
TOOL_CONFIGS = {
    "claude-code": {
        "name": "Claude Code",
        "skill_dir": "~/.claude/skills",
        "check_paths": ["~/.claude/skills"],
    },
    "codex-cli": {
        "name": "Codex CLI (OpenAI)",
        "skill_dir": "~/.codex/skills",
        "check_paths": ["~/.codex/skills"],
    },
    "codex-engine": {
        "name": "Codex Engine",
        "skill_dir": "~/.codefuse/engine/codex/skills",
        "check_paths": ["~/.codefuse/engine/codex/skills"],
    },
    "codefuse": {
        "name": "CodeFuse",
        "skill_dir": "~/.codefuse/engine/cc/skills",
        "check_paths": ["~/.codefuse/engine/cc/skills"],
    },
    "windsurf": {
        "name": "Windsurf",
        "skill_dir": "~/.codeium/windsurf/skills",
        "check_paths": ["~/.codeium/windsurf/skills"],
    },
    "openclaw": {
        "name": "OpenClaw",
        "skill_dir": "~/.openclaw/workspace/skills",
        "check_paths": ["~/.openclaw/workspace/skills"],
    },
    "opencode": {
        "name": "OpenCode",
        "skill_dir": "~/.opencode/skills",
        "check_paths": ["~/.opencode/skills"],
    },
    "homiclaw": {
        "name": "Homiclaw",
        "skill_dir": "~/.homiclaw/workspace/user-skills",
        "check_paths": ["~/.homiclaw/workspace/user-skills"],
    },
    "agents": {
        "name": "Agents",
        "skill_dir": "~/.agents/skills",
        "check_paths": ["~/.agents/skills"],
    },
}


def expand_path(path: str) -> Path:
    """展开路径中的 ~ 和环境变量"""
    return Path(os.path.expanduser(os.path.expandvars(path)))


def get_skill_version(skill_path: Path) -> str:
    """
    从 package.json 读取 skill 版本号

    Args:
        skill_path: skill 目录路径

    Returns:
        版本号，如果不存在则返回 "未知"
    """
    pkg_file = skill_path / "package.json"
    if pkg_file.exists():
        try:
            with open(pkg_file, 'r', encoding='utf-8') as f:
                pkg_data = json.load(f)
                return pkg_data.get('version', '未知')
        except (json.JSONDecodeError, IOError):
            pass
    return '未知'


MANIFEST_PATH = Path.home() / ".claude" / "skills" / ".skills-manifest.json"


def load_manifest() -> dict:
    """加载 Manifest 文件"""
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"skills": {}}


def save_manifest(manifest: dict) -> None:
    """保存 Manifest 文件"""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def update_manifest(skill_path: Path, tool_key: str, version: str) -> None:
    """
    更新 Manifest 记录

    Args:
        skill_path: skill 目录路径
        tool_key: 工具标识
        version: skill 版本号
    """
    manifest = load_manifest()
    skill_name = skill_path.name
    tool_config = TOOL_CONFIGS[tool_key]

    if skill_name not in manifest["skills"]:
        manifest["skills"][skill_name] = {
            "version": version,
            "installedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "package": f"@your-scope/{skill_name}",
            "path": f"{tool_config['skill_dir']}/{skill_name}",
            "target": tool_key,
            "sourcePath": str(skill_path)
        }
    else:
        manifest["skills"][skill_name]["version"] = version
        manifest["skills"][skill_name]["path"] = f"{tool_config['skill_dir']}/{skill_name}"
        manifest["skills"][skill_name]["target"] = tool_key

    save_manifest(manifest)


def detect_skill_dirs() -> List[Dict]:
    """
    检测本机所有存在的 skills 目录

    Returns:
        存在的 skills 目录列表，每项包含 tool_key, name, path
    """
    detected = []
    for tool_key, config in TOOL_CONFIGS.items():
        skill_dir = expand_path(config["skill_dir"])
        if skill_dir.exists():
            detected.append({
                "tool_key": tool_key,
                "name": config["name"],
                "path": skill_dir
            })
    return detected


def find_skill_in_dirs(skill_name: str, dirs: List[Dict]) -> Optional[Path]:
    """
    在指定目录列表中查找 skill

    Args:
        skill_name: skill 名称
        dirs: 目录列表（detect_skill_dirs 的返回值）

    Returns:
        skill 路径，如果未找到返回 None
    """
    for dir_info in dirs:
        skill_path = dir_info["path"] / skill_name
        if skill_path.exists() and (skill_path / "SKILL.md").exists():
            return skill_path
    return None


def find_skill_source(skill_name: str) -> Optional[Path]:
    """
    查找 skill 源目录，优先级：
    1. 当前工作目录
    2. 本机所有 skills 目录
    3. Manifest 记录

    Args:
        skill_name: skill 名称

    Returns:
        skill 源路径，如果未找到返回 None
    """
    # 1. 检查当前工作目录
    cwd = Path.cwd()
    if (cwd / "SKILL.md").exists() and cwd.name == skill_name:
        return cwd

    # 检查当前目录的子目录
    skill_in_cwd = cwd / skill_name
    if skill_in_cwd.exists() and (skill_in_cwd / "SKILL.md").exists():
        return skill_in_cwd

    # 2. 检查 Manifest 记录
    manifest = load_manifest()
    if skill_name in manifest.get("skills", {}):
        source_path = manifest["skills"][skill_name].get("sourcePath")
        if source_path and Path(source_path).exists():
            return Path(source_path)

    # 3. 扫描本机所有 skills 目录
    detected_dirs = detect_skill_dirs()
    skill_path = find_skill_in_dirs(skill_name, detected_dirs)
    if skill_path:
        # 检查是否是软链接，如果是则返回真实路径
        if skill_path.is_symlink():
            return skill_path.resolve()
        return skill_path

    return None


def list_all_skills() -> Dict[str, List[Dict]]:
    """
    列出所有检测到的 skills 目录中的 skill

    Returns:
        按目录分组的 skill 列表
    """
    result = {}
    detected_dirs = detect_skill_dirs()

    for dir_info in detected_dirs:
        skill_dir = dir_info["path"]
        skills = []

        for item in skill_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                is_symlink = item.is_symlink()
                real_path = item.resolve() if is_symlink else item
                version = get_skill_version(real_path)
                skills.append({
                    "name": item.name,
                    "version": version,
                    "is_symlink": is_symlink,
                    "real_path": str(real_path)
                })

        if skills:
            result[dir_info["name"]] = {
                "path": str(skill_dir),
                "skills": sorted(skills, key=lambda x: x["name"])
            }

    return result


def get_skill_status(skill_path: Path) -> dict:
    """
    获取 skill 在各路径的同步状态

    Args:
        skill_path: skill 目录路径

    Returns:
        状态信息字典
    """
    skill_name = skill_path.name
    version = get_skill_version(skill_path)
    status = {
        "name": skill_name,
        "version": version,
        "sourcePath": str(skill_path),
        "paths": {}
    }

    detected_dirs = detect_skill_dirs()
    for dir_info in detected_dirs:
        tool_key = dir_info["tool_key"]
        target_dir = dir_info["path"]
        target_link = target_dir / skill_name

        if target_link.is_symlink():
            existing_target = target_link.resolve()
            if existing_target == skill_path.resolve():
                status["paths"][tool_key] = {"status": "✅", "note": "已同步"}
            else:
                status["paths"][tool_key] = {"status": "❌", "note": f"指向其他源: {existing_target.name}"}
        elif target_link.exists():
            status["paths"][tool_key] = {"status": "⚠️", "note": "真实目录"}
        else:
            status["paths"][tool_key] = {"status": "-", "note": "未链接"}

    return status


def find_skill_directory(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    查找 skill 目录（包含 SKILL.md 的目录）

    Args:
        start_path: 开始搜索的路径，默认为当前目录

    Returns:
        skill 目录路径，如果未找到返回 None
    """
    if start_path is None:
        start_path = Path.cwd()

    # 检查当前目录
    if (start_path / "SKILL.md").exists():
        return start_path

    # 检查父目录（最多向上 3 层）
    current = start_path
    for _ in range(3):
        parent = current.parent
        if parent == current:  # 已到达根目录
            break
        if (parent / "SKILL.md").exists():
            return parent
        current = parent

    return None


def create_symlink(skill_path: Path, target_dir: Path, dry_run: bool = False) -> bool:
    """
    创建软连接

    Args:
        skill_path: skill 源目录
        target_dir: 目标 skills 目录
        dry_run: 是否只模拟执行

    Returns:
        是否成功
    """
    skill_name = skill_path.name
    target_link = target_dir / skill_name

    # 确保目标目录存在
    if not target_dir.exists():
        if dry_run:
            print(f"    [DRY-RUN] Would create directory: {target_dir}")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)

    # 检查目标是否已存在
    if target_link.exists() or target_link.is_symlink():
        if target_link.is_symlink():
            existing_target = target_link.resolve()
            if existing_target == skill_path.resolve():
                print(f"    ✓ Already linked: {target_link}")
                return True
            else:
                if dry_run:
                    print(f"    [DRY-RUN] Would remove existing symlink: {target_link}")
                else:
                    target_link.unlink()
        else:
            # 是真实目录，不是软连接
            print(f"    ⚠ Skipping: {target_link} exists as a real directory")
            return False

    # 创建软连接
    if dry_run:
        print(f"    [DRY-RUN] Would create symlink: {target_link} -> {skill_path}")
    else:
        try:
            target_link.symlink_to(skill_path)
            print(f"    ✓ Created: {target_link} -> {skill_path}")
            return True
        except OSError as e:
            print(f"    ✗ Failed: {e}")
            return False

    return True


def remove_symlink(skill_path: Path, target_dir: Path) -> bool:
    """
    删除软连接

    Args:
        skill_path: skill 源目录
        target_dir: 目标 skills 目录

    Returns:
        是否成功
    """
    skill_name = skill_path.name
    target_link = target_dir / skill_name

    if not target_link.exists() and not target_link.is_symlink():
        print(f"    - Not found: {target_link}")
        return True

    if target_link.is_symlink():
        existing_target = target_link.resolve()
        if existing_target == skill_path.resolve():
            target_link.unlink()
            print(f"    ✓ Removed: {target_link}")
            return True
        else:
            print(f"    ⚠ Skipping: {target_link} points to different target")
            return False
    else:
        print(f"    ⚠ Skipping: {target_link} is a real directory, not a symlink")
        return False


def sync_skill(skill_path: Path, dry_run: bool = False, unlink: bool = False) -> dict:
    """
    同步 skill 到所有已安装的工具

    Args:
        skill_path: skill 目录路径
        dry_run: 是否只模拟执行
        unlink: 是否删除软连接

    Returns:
        操作结果统计
    """
    results = {"detected": [], "success": [], "skipped": [], "failed": []}

    # 获取版本号
    version = get_skill_version(skill_path)

    print(f"\n📁 Skill: {skill_path}")
    print(f"   Name: {skill_path.name}")
    print(f"   Version: {version}")
    print()

    # 检测已安装的工具目录
    print("🔍 Detecting skill directories on this machine...")
    detected_dirs = detect_skill_dirs()

    if not detected_dirs:
        print("   ⚠ No skill directories detected!")
        return results

    for dir_info in detected_dirs:
        results["detected"].append(dir_info["tool_key"])
        print(f"   ✓ {dir_info['name']}: {dir_info['path']}")

    print()

    # 执行同步/取消同步
    action = "Unlinking" if unlink else ("Syncing" if not dry_run else "[DRY-RUN] Would sync")
    print(f"🔗 {action} skill to detected directories...")

    for dir_info in detected_dirs:
        tool_key = dir_info["tool_key"]
        target_dir = dir_info["path"]

        print(f"\n   [{dir_info['name']}]")

        if unlink:
            success = remove_symlink(skill_path, target_dir)
        else:
            success = create_symlink(skill_path, target_dir, dry_run)

        if success and not dry_run and not unlink:
            # 同步成功后更新 Manifest
            update_manifest(skill_path, tool_key, version)
            results["success"].append(tool_key)
        elif success:
            results["success"].append(tool_key)
        else:
            results["failed"].append(tool_key)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Sync skill to all installed AI coding tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    sync_skill.py                           # Auto-detect skill in current directory
    sync_skill.py /path/to/my-skill         # Specify skill directory
    sync_skill.py --skill my-skill          # Find and sync skill by name
    sync_skill.py --dry-run                 # Show what would be done
    sync_skill.py --unlink                  # Remove existing symlinks
    sync_skill.py --detect-dirs             # Detect skill directories on this machine
    sync_skill.py --list-skills             # List all skills in detected directories
    sync_skill.py --status                  # Show sync status

Supported Skill Directories:
    - Claude Code    (~/.claude/skills)
    - Codex CLI      (~/.codex/skills)
    - Codex Engine   (~/.codefuse/engine/codex/skills)
    - CodeFuse       (~/.codefuse/engine/cc/skills)
    - Windsurf       (~/.codeium/windsurf/skills)
    - OpenClaw       (~/.openclaw/workspace/skills)
    - OpenCode       (~/.opencode/skills)
    - Homiclaw       (~/.homiclaw/workspace/user-skills)
    - Agents         (~/.agents/skills)
        """,
    )
    parser.add_argument(
        "skill_path",
        nargs="?",
        help="Path to skill directory (default: auto-detect from current directory)",
    )
    parser.add_argument(
        "--skill",
        dest="skill_name",
        help="Skill name to find and sync (searches cwd, manifest, and skill directories)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--unlink",
        action="store_true",
        help="Remove symlinks instead of creating them",
    )
    parser.add_argument(
        "--detect-dirs",
        action="store_true",
        help="Detect all skill directories on this machine",
    )
    parser.add_argument(
        "--list-skills",
        action="store_true",
        help="List all skills in detected directories",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show sync status of skill across all directories",
    )

    args = parser.parse_args()

    # 检测本机 skills 目录
    if args.detect_dirs:
        print("\n🔍 Detecting skill directories on this machine...\n")
        detected_dirs = detect_skill_dirs()

        if not detected_dirs:
            print("   ⚠ No skill directories detected!")
            return 0

        print(f"   Found {len(detected_dirs)} skill directories:\n")
        for dir_info in detected_dirs:
            print(f"   ✓ {dir_info['name']}")
            print(f"     Path: {dir_info['path']}")
            print()

        return 0

    # 列出所有 skill
    if args.list_skills:
        print("\n📋 Listing all skills in detected directories...\n")
        all_skills = list_all_skills()

        if not all_skills:
            print("   ⚠ No skills found in any directory!")
            return 0

        total_skills = sum(len(info["skills"]) for info in all_skills.values())
        print(f"   Found {total_skills} skills in {len(all_skills)} directories:\n")

        for tool_name, info in all_skills.items():
            print(f"   📁 {tool_name}")
            print(f"      Path: {info['path']}")
            for skill in info["skills"]:
                link_status = "→" if skill["is_symlink"] else "•"
                print(f"      {link_status} {skill['name']} (v{skill['version']})")
            print()

        return 0

    # 显示同步状态
    if args.status:
        # 确定 skill 目录
        if args.skill_name:
            skill_path = find_skill_source(args.skill_name)
            if not skill_path:
                print(f"❌ Error: Skill '{args.skill_name}' not found")
                print("   Searched in:")
                print("   - Current working directory")
                print("   - Manifest records")
                print("   - All detected skill directories")
                return 1
        elif args.skill_path:
            skill_path = Path(args.skill_path).resolve()
            if not skill_path.is_dir():
                print(f"❌ Error: Not a directory: {skill_path}")
                return 1
        else:
            skill_path = find_skill_directory()
            if not skill_path:
                print("❌ Error: Could not find skill directory (no SKILL.md found)")
                print("   Please specify the skill path or use --skill <name>")
                return 1

        status = get_skill_status(skill_path)

        print(f"\n📊 Skill 同步状态")
        print(f"\n## {status['name']} (v{status['version']})")
        print(f"\n| 工具 | 状态 | 说明 |")
        print(f"|------|------|------|")
        for tool_key, info in status["paths"].items():
            tool_name = TOOL_CONFIGS[tool_key]["name"]
            print(f"| {tool_name} | {info['status']} | {info['note']} |")
        print(f"\n> 源路径: {status['sourcePath']}")
        return 0

    # 确定 skill 目录
    if args.skill_name:
        # 按名称查找
        skill_path = find_skill_source(args.skill_name)
        if not skill_path:
            print(f"❌ Error: Skill '{args.skill_name}' not found")
            print("\n   Searched in:")
            print("   1. Current working directory")
            print("   2. Manifest records (~/.claude/skills/.skills-manifest.json)")
            print("   3. All detected skill directories")
            print("\n   Please provide the skill path directly:")
            print(f"   sync_skill.py /path/to/{args.skill_name}")
            return 1
        print(f"✓ Found skill: {skill_path}")
    elif args.skill_path:
        skill_path = Path(args.skill_path).resolve()
        if not skill_path.is_dir():
            print(f"❌ Error: Not a directory: {skill_path}")
            return 1
        if not (skill_path / "SKILL.md").exists():
            print(f"⚠ Warning: No SKILL.md found in {skill_path}")
    else:
        skill_path = find_skill_directory()
        if not skill_path:
            print("❌ Error: Could not find skill directory (no SKILL.md found)")
            print("   Please specify the skill path or use --skill <name>")
            return 1

    # 执行同步
    results = sync_skill(skill_path, dry_run=args.dry_run, unlink=args.unlink)

    # 打印摘要
    print("\n" + "=" * 50)
    if results["detected"]:
        print(f"📁 Detected {len(results['detected'])} skill directories")
    if results["success"]:
        print(f"✓ {len(results['success'])} directory(s) processed successfully")
    if results["failed"]:
        print(f"✗ {len(results['failed'])} directory(s) failed")

    return 0 if not results.get("failed") else 1


if __name__ == "__main__":
    sys.exit(main())