#!/usr/bin/env python3
"""
skillctl - 本地 Skill 中央仓库管理工具

核心理念（类似 pnpm store）：
    所有 skill 统一存放在中央仓库 ~/.skill-store/store/，
    通过软链接分发到各 AI 编程工具的 skills 目录。

子命令：
    install     从本地/git/private-npm/url 安装 skill 到中央仓库并分发
    uninstall   从中央仓库卸载 skill 并清理所有软链
    update      更新 skill（重新拉取最新版本）
    adopt       反向归集：把已存在于 AI 工具目录的 skill 收编到中央仓库
    list        列出中央仓库中的 skill / 各工具中的 skill
    link        把中央仓库中的 skill 链接到工具
    unlink      从工具中移除链接（不删除中央仓库内容）
    detect      检测本机已安装的 AI 工具
    store       查看/设置中央仓库根路径
    status      查看 skill 在各工具中的链接状态

Examples:
    skillctl install ./my-skill
    skillctl install https://github.com/user/skill.git
    skillctl install @your-scope/skill-name
    skillctl install https://example.com/skill.zip
    skillctl uninstall my-skill
    skillctl adopt --all
    skillctl list
    skillctl store --show
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# 让本脚本既能作为模块执行，也能直接 ./skillctl.py 运行
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import adopter, batch, config, linker, manifest, sources, store, tools


def _parse_link_type(args) -> str:
    """从 --copy / --symlink 标志解析出 link_type"""
    if getattr(args, "copy", False):
        return linker.LINK_TYPE_COPY
    if getattr(args, "symlink", False):
        return linker.LINK_TYPE_SYMLINK
    return linker.LINK_TYPE_AUTO


def _scope_cwd(args) -> Optional[Path]:
    """project scope 时取 --cwd 或 Path.cwd()，其它返回 None"""
    if getattr(args, "scope", "global") != "project":
        return None
    cwd_arg = getattr(args, "cwd", None)
    return Path(cwd_arg).resolve() if cwd_arg else Path.cwd()


def _scope_project_root(args, cwd: Optional[Path]) -> Optional[str]:
    """project_root（用于写 manifest）的字符串形式"""
    if getattr(args, "scope", "global") != "project" or cwd is None:
        return None
    return str(cwd)


# ===========================================================================
# 通用输出工具
# ===========================================================================

def _print_kv(items):
    """打印 key:value 列表，对齐冒号"""
    if not items:
        return
    width = max(len(k) for k, _ in items)
    for k, v in items:
        print(f"  {k.ljust(width)} : {v}")


def _emit_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ===========================================================================
# install
# ===========================================================================

def cmd_install(args) -> int:
    config.ensure_initialized()

    # 0. 如果 source 是 .txt 文件，走批量安装分支
    src_path = Path(args.source)
    if src_path.exists() and src_path.is_file() and src_path.suffix.lower() == ".txt":
        return _cmd_install_batch(args, src_path)

    # 1. 下载/识别源
    try:
        skill_dir, version, source_type, source_ref = sources.install(
            args.source,
            source_type=args.type,
            git_ref=args.ref,
        )
    except Exception as e:
        print(f"❌ 安装失败: {e}", file=sys.stderr)
        return 1

    skill_name = args.name or skill_dir.name
    print(f"📦 解析成功:")
    _print_kv([
        ("name", skill_name),
        ("version", version),
        ("source_type", source_type),
        ("source_ref", source_ref),
        ("source_dir", str(skill_dir)),
    ])

    if args.dry_run:
        print("\n[DRY-RUN] 已跳过实际写入仓库与软链分发")
        return 0

    # 2. 加入中央仓库
    try:
        if source_type == "local":
            store_path = store.add_skill_from_path(
                skill_dir, name=skill_name, overwrite=args.force, move=False,
            )
        else:
            # git/private-npm/url 都是临时目录，直接 move 进 store 节省空间
            store_path = store.add_skill_from_path(
                skill_dir, name=skill_name, overwrite=args.force, move=True,
            )
    except FileExistsError:
        print(f"❌ 中央仓库已存在同名 skill: {skill_name}（使用 --force 覆盖）", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 加入中央仓库失败: {e}", file=sys.stderr)
        return 1

    print(f"✅ 已加入中央仓库: {store_path}")

    # 3. 分发软链（按 scope）
    cwd = _scope_cwd(args)
    project_root = _scope_project_root(args, cwd)
    link_type = _parse_link_type(args)

    scopes_to_link = ["global", "project"] if args.scope == "both" else [args.scope]
    all_link_results: dict = {}

    for sc in scopes_to_link:
        sc_cwd = cwd if sc == "project" else None
        targets = args.targets.split(",") if args.targets else None
        link_results = linker.link_to_all(
            store_path, targets=targets, scope=sc, cwd=sc_cwd,
            link_type=link_type,
        )
        print(f"\n🔗 软链分发 [scope={sc}]:")
        for tk, r in link_results.items():
            icon = "✓" if r["ok"] else "✗"
            lt = r.get("link_type") or "-"
            print(f"  {icon} {tools.get_tool_name(tk)}: {r['note']} [{lt}]")
        all_link_results[sc] = link_results

    # 4. 写 manifest（保留每条 link 的 scope/link_type/project_root）
    manifest.add_skill_entry(
        name=skill_name,
        version=version,
        source_type=source_type,
        source_ref=source_ref,
        linked_targets=[],  # 先清空，下面分别 add
    )
    n_linked = 0
    for sc, link_results in all_link_results.items():
        sc_root = project_root if sc == "project" else None
        for tk, r in link_results.items():
            if r.get("ok") and r.get("action") in ("created", "kept"):
                manifest.add_linked_target(
                    skill_name, tool_key=tk, scope=sc,
                    link_type=r.get("link_type", linker.LINK_TYPE_SYMLINK),
                    project_root=sc_root,
                )
                n_linked += 1
    print(f"\n📝 已写入 manifest（linked to {n_linked} 条记录）")
    return 0


def _cmd_install_batch(args, txt_path: Path) -> int:
    """skillctl install <skills.txt> 的实现"""
    config.ensure_initialized()

    cwd = _scope_cwd(args)
    link_type = _parse_link_type(args)
    auto_link = args.scope != "none"  # scope=none 时不自动 link
    link_scope = args.scope if args.scope in ("global", "project") else "global"

    print(f"📥 批量安装来自: {txt_path}\n")

    if args.scope == "both":
        # both 模式：先 global 再 project，两次 install_from_file
        # 但 install 本身只发生一次（不能重复 install），所以分两步：
        # 1) install_from_file 不 auto_link
        # 2) 用 sync_from_file 双 scope link
        result = batch.install_from_file(
            txt_path, force=args.force, auto_link=False, dry_run=args.dry_run,
        )
        _print_batch_result(result, dry_run=args.dry_run)
        if args.dry_run or not result["success"]:
            return 0 if not result["failed"] else 1
        # 双 scope link
        for sc in ("global", "project"):
            sc_cwd = cwd if sc == "project" else None
            print(f"\n🔗 同步 link [scope={sc}]:")
            sync = batch.sync_from_file(
                txt_path, scope=sc, cwd=sc_cwd, link_type=link_type,
            )
            for r in sync["success"]:
                print(f"  · {r['name']}: {len(r['results'])} 个 target")
        return 0 if not result["failed"] else 1

    # global / project / none 模式
    result = batch.install_from_file(
        txt_path,
        force=args.force,
        auto_link=auto_link,
        link_scope=link_scope,
        link_cwd=cwd,
        link_type=link_type,
        dry_run=args.dry_run,
    )
    _print_batch_result(result, dry_run=args.dry_run)
    return 0 if not result["failed"] else 1


def _print_batch_result(result: dict, *, dry_run: bool = False) -> None:
    """格式化打印 batch.install_from_file 的返回结果"""
    success = result.get("success", [])
    failed = result.get("failed", [])
    skipped = result.get("skipped", [])

    if success:
        head = "[DRY-RUN] 将安装" if dry_run else "✅ 已安装"
        print(f"{head}（{len(success)} 项）:")
        for r in success:
            line_no = r.get("line_no", "?")
            name = r.get("name") or "?"
            ver = r.get("version") or "?"
            stype = r.get("type") or "?"
            print(f"  · L{line_no}: {name}@{ver} ({stype})  ← {r['source']}")
    if skipped:
        print(f"\n⏭  跳过（{len(skipped)} 项，已存在，加 --force 覆盖）:")
        for r in skipped:
            print(f"  · L{r['line_no']}: {r.get('name', r['source'])}: {r['error']}")
    if failed:
        print(f"\n❌ 失败（{len(failed)} 项）:", file=sys.stderr)
        for r in failed:
            print(f"  · L{r['line_no']}: {r['source']}: {r['error']}", file=sys.stderr)


# ===========================================================================
# uninstall
# ===========================================================================

def cmd_uninstall(args) -> int:
    config.ensure_initialized()
    skill_name = args.name

    store_path = store.get_skill_path(skill_name)
    if not store.has_skill(skill_name) and not manifest.get_skill_entry(skill_name):
        print(f"❌ 未找到 skill: {skill_name}", file=sys.stderr)
        return 1

    print(f"🗑  卸载 {skill_name}")

    # 1. 移除所有软链
    if store.has_skill(skill_name):
        unlink_results = linker.unlink_from_all(store_path, dry_run=args.dry_run)
        print("\n🔗 移除软链:")
        for tk, r in unlink_results.items():
            icon = "✓" if r["ok"] else "·"
            print(f"  {icon} {tools.get_tool_name(tk)}: {r['note']}")

    # 2. 删除中央仓库实体
    if not args.keep_store:
        if args.dry_run:
            print(f"\n  [DRY-RUN] 将删除中央仓库目录: {store_path}")
        else:
            store.remove_skill(skill_name)
            print(f"\n🧹 已删除中央仓库目录: {store_path}")

    # 3. 清理 manifest
    if not args.dry_run and not args.keep_store:
        manifest.remove_skill_entry(skill_name)
        print("📝 已清理 manifest 记录")

    return 0


# ===========================================================================
# update
# ===========================================================================

def cmd_update(args) -> int:
    config.ensure_initialized()
    skill_name = args.name

    entry = manifest.get_skill_entry(skill_name)
    if not entry:
        print(f"❌ manifest 中未找到 skill: {skill_name}", file=sys.stderr)
        return 1

    src = entry["source"]
    src_type = src["type"]
    src_ref = src["ref"]

    if src_type == "adopted":
        print(f"⚠️  {skill_name} 来源是 adopted（无远程源），无法 update", file=sys.stderr)
        return 1

    print(f"🔄 更新 {skill_name}（来源: {src_type} {src_ref}）")

    try:
        skill_dir, version, _, _ = sources.install(src_ref, source_type=src_type)
    except Exception as e:
        print(f"❌ 拉取最新失败: {e}", file=sys.stderr)
        return 1

    # 覆盖中央仓库
    move = (src_type != "local")
    store.add_skill_from_path(skill_dir, name=skill_name, overwrite=True, move=move)

    # manifest 更新
    manifest.add_skill_entry(
        name=skill_name,
        version=version,
        source_type=src_type,
        source_ref=src_ref,
        linked_targets=entry.get("linked_targets", []),
    )
    print(f"✅ 已更新到版本 {version}")
    return 0


# ===========================================================================
# adopt
# ===========================================================================

def cmd_adopt(args) -> int:
    config.ensure_initialized()

    if args.all:
        results = adopter.adopt_all(
            backup=not args.no_backup,
            overwrite_store=args.overwrite,
            relink_all=not args.no_relink,
            dry_run=args.dry_run,
            tool_filter=args.tool,
        )
    else:
        if not args.tool or not args.name:
            print("❌ 单个归集必须指定 --tool <key> 和 --name <skill>，或使用 --all", file=sys.stderr)
            return 1
        results = [{
            "tool_key": args.tool,
            "skill": args.name,
            **adopter.adopt_skill(
                args.tool, args.name,
                backup=not args.no_backup,
                overwrite_store=args.overwrite,
                relink_all=not args.no_relink,
                dry_run=args.dry_run,
            ),
        }]

    if args.json:
        _emit_json(results)
        return 0

    if not results:
        print("（没有可归集的真实 skill 目录）")
        return 0

    print(f"\n📥 反向归集结果（共 {len(results)} 项）:\n")
    for r in results:
        icon = "✓" if r.get("ok") else "·"
        print(f"  {icon} [{r.get('tool_key')}] {r.get('skill')}: {r.get('note')}")
        if r.get("backup_path"):
            print(f"      备份: {r['backup_path']}")
    return 0


# ===========================================================================
# list
# ===========================================================================

def cmd_list(args) -> int:
    config.ensure_initialized()

    if args.tools:
        # 列出各工具下现存 skill
        items = adopter.scan_existing_skills(only_real=False)
        if args.json:
            _emit_json(items)
            return 0
        if not items:
            print("（未在任何工具目录中发现 skill）")
            return 0
        print(f"\n🛠  各工具中的 skill（共 {len(items)} 项）:\n")
        for it in items:
            arrow = "→" if it["is_symlink"] else "•"
            extra = f" → {it['points_to']}" if it["is_symlink"] else ""
            print(f"  [{it['tool_key']}] {arrow} {it['name']} (v{it['version']}){extra}")
        return 0

    # 默认：列出中央仓库 + manifest
    store_items = store.list_store_skills()
    mani = manifest.list_skills()

    if args.json:
        _emit_json({"store": store_items, "manifest": mani})
        return 0

    if not store_items:
        print(f"📦 中央仓库为空: {config.get_store_dir()}")
        return 0

    print(f"\n📦 中央仓库 ({config.get_store_dir()}):\n")
    for it in store_items:
        m = mani.get(it["name"], {})
        src = m.get("source", {})
        targets = m.get("linked_targets", [])
        print(f"  • {it['name']} (v{it['version']})")
        if src:
            print(f"      来源: {src.get('type')}  {src.get('ref')}")
        if targets:
            print(f"      已链接: {', '.join(targets)}")
    return 0


# ===========================================================================
# link / unlink
# ===========================================================================

def cmd_link(args) -> int:
    config.ensure_initialized()
    if not store.has_skill(args.name):
        print(f"❌ 中央仓库中未找到 skill: {args.name}", file=sys.stderr)
        return 1
    store_path = store.get_skill_path(args.name)
    targets = args.targets.split(",") if args.targets else None
    cwd = _scope_cwd(args)
    project_root = _scope_project_root(args, cwd)
    link_type = _parse_link_type(args)

    scopes_to_link = ["global", "project"] if args.scope == "both" else [args.scope]
    print(f"\n🔗 链接 {args.name}:")
    for sc in scopes_to_link:
        sc_cwd = cwd if sc == "project" else None
        sc_root = project_root if sc == "project" else None
        results = linker.link_to_all(
            store_path, targets=targets, scope=sc, cwd=sc_cwd,
            link_type=link_type, dry_run=args.dry_run,
        )
        print(f"  [scope={sc}]")
        for tk, r in results.items():
            icon = "✓" if r["ok"] else "✗"
            lt = r.get("link_type") or "-"
            print(f"    {icon} {tools.get_tool_name(tk)}: {r['note']} [{lt}]")
            if (not args.dry_run) and r.get("ok") and r.get("action") in ("created", "kept"):
                manifest.add_linked_target(
                    args.name, tool_key=tk, scope=sc,
                    link_type=r.get("link_type", linker.LINK_TYPE_SYMLINK),
                    project_root=sc_root,
                )
    return 0


def cmd_unlink(args) -> int:
    config.ensure_initialized()
    store_path = store.get_skill_path(args.name)
    if not store.has_skill(args.name):
        print(f"❌ 中央仓库中未找到 skill: {args.name}", file=sys.stderr)
        return 1
    targets = args.targets.split(",") if args.targets else None
    cwd = _scope_cwd(args)
    project_root = _scope_project_root(args, cwd)

    scopes_to_unlink = ["global", "project"] if args.scope == "both" else [args.scope]
    print(f"\n🔗 解除链接 {args.name}:")
    for sc in scopes_to_unlink:
        sc_cwd = cwd if sc == "project" else None
        sc_root = project_root if sc == "project" else None
        results = linker.unlink_from_all(
            store_path, targets=targets, scope=sc, cwd=sc_cwd, dry_run=args.dry_run,
        )
        print(f"  [scope={sc}]")
        for tk, r in results.items():
            icon = "✓" if r["ok"] else "·"
            print(f"    {icon} {tools.get_tool_name(tk)}: {r['note']}")
            if (not args.dry_run) and r.get("ok") and r.get("action") in ("removed", "would-remove"):
                manifest.remove_linked_target(
                    args.name, tool_key=tk, scope=sc, project_root=sc_root,
                )
    return 0


# ===========================================================================
# export / sync (skills.txt 批量管理)
# ===========================================================================

def cmd_export(args) -> int:
    """从 manifest 导出 skills.txt"""
    config.ensure_initialized()
    out_path = Path(args.output) if args.output else None
    content = batch.export_skills_txt(
        out_path=out_path, include_comments=not args.no_comments,
    )
    if out_path:
        print(f"✅ 已导出到 {out_path}")
    else:
        sys.stdout.write(content)
    return 0


def cmd_sync(args) -> int:
    """
    同步：把 skill 链接到工具目录（不下载）。

    两种用法：
      skillctl sync <skill-name>      # 单个 skill
      skillctl sync <skills.txt>      # 批量
    """
    config.ensure_initialized()
    target_path = Path(args.target)
    cwd = _scope_cwd(args)
    project_root = _scope_project_root(args, cwd)
    link_type = _parse_link_type(args)
    targets = args.targets.split(",") if args.targets else None

    if (target_path.exists() and target_path.is_file()
            and target_path.suffix.lower() == ".txt"):
        scopes = ["global", "project"] if args.scope == "both" else [args.scope]
        any_fail = False
        for sc in scopes:
            sc_cwd = cwd if sc == "project" else None
            print(f"\n🔗 批量同步 [scope={sc}] from {target_path}:")
            result = batch.sync_from_file(
                target_path, scope=sc, cwd=sc_cwd, targets=targets,
                link_type=link_type, dry_run=args.dry_run,
            )
            for r in result["success"]:
                ok_count = sum(1 for x in r["results"].values() if x.get("ok"))
                print(f"  ✓ L{r['line_no']} {r['name']}: {ok_count}/{len(r['results'])} targets")
            for f in result["failed"]:
                print(f"  ✗ L{f['line_no']} {f['source']}: {f['error']}", file=sys.stderr)
                any_fail = True
        return 1 if any_fail else 0

    if not store.has_skill(args.target):
        print(f"❌ 中央仓库中未找到 skill: {args.target}", file=sys.stderr)
        return 1
    store_path = store.get_skill_path(args.target)
    scopes = ["global", "project"] if args.scope == "both" else [args.scope]
    print(f"\n🔗 同步 {args.target}:")
    for sc in scopes:
        sc_cwd = cwd if sc == "project" else None
        sc_root = project_root if sc == "project" else None
        results = linker.link_to_all(
            store_path, targets=targets, scope=sc, cwd=sc_cwd,
            link_type=link_type, dry_run=args.dry_run,
        )
        print(f"  [scope={sc}]")
        for tk, r in results.items():
            icon = "✓" if r["ok"] else "✗"
            lt = r.get("link_type") or "-"
            print(f"    {icon} {tools.get_tool_name(tk)}: {r['note']} [{lt}]")
            if (not args.dry_run) and r.get("ok") and r.get("action") in ("created", "kept"):
                manifest.add_linked_target(
                    args.target, tool_key=tk, scope=sc,
                    link_type=r.get("link_type", linker.LINK_TYPE_SYMLINK),
                    project_root=sc_root,
                )
    return 0


# ===========================================================================
# scan（通用扫描：包含未知工具，按路径推断）
# ===========================================================================

def cmd_scan(args) -> int:
    """
    通用扫描：发现本机所有疑似 AI 工具的 skills 目录。

    与 detect 的区别：scan 展示**全部**扫描结果（含未在别名表中的未知工具）
    及其推断信息，便于用户检视通用扫描机制的识别结果。
    """
    discovered = tools.discover_skill_dirs(
        max_depth=args.max_depth,
        include_empty=args.include_empty,
        refresh=args.refresh,
    )

    if args.json:
        _emit_json([
            {
                "tool_key": d["tool_key"],
                "name": d["name"],
                "path": str(d["path"]),
                "alias": d["alias"],
                "has_skills": d["has_skills"],
            }
            for d in discovered
        ])
        return 0

    if not discovered:
        print("⚠ 未扫描到任何符合结构的 skills 目录")
        return 0

    alias_count = sum(1 for d in discovered if d["alias"])
    inferred_count = len(discovered) - alias_count
    print(f"\n🔍 扫描发现 {len(discovered)} 个 skills 目录"
          f"（已知别名 {alias_count}，路径推断 {inferred_count}）:\n")
    for d in discovered:
        tag = "🏷  别名" if d["alias"] else "🔮 推断"
        skills_mark = "✓" if d["has_skills"] else "∅ 空"
        print(f"  {tag}  [{d['tool_key']}]  {d['name']}  ({skills_mark})")
        print(f"        {d['path']}\n")
    return 0

# ===========================================================================
# detect
# ===========================================================================

def cmd_detect(args) -> int:
    detected = tools.detect_skill_dirs()
    if args.json:
        _emit_json([
            {"tool_key": d["tool_key"], "name": d["name"], "path": str(d["path"])}
            for d in detected
        ])
        return 0
    if not detected:
        print("⚠ 未检测到任何 AI 工具的 skills 目录")
        return 0
    print(f"\n🔍 检测到 {len(detected)} 个 AI 工具:\n")
    for d in detected:
        print(f"  ✓ {d['name']}")
        print(f"      key:  {d['tool_key']}")
        print(f"      path: {d['path']}\n")
    return 0


# ===========================================================================
# store
# ===========================================================================

def cmd_store(args) -> int:
    if args.set:
        cfg = config.set_store_home(args.set)
        print(f"✅ 已更新中央仓库路径: {cfg['store_home']}")
        print("   注意：本命令仅修改配置，不会自动迁移已有数据")
        return 0

    config.ensure_initialized()
    print("\n📦 中央仓库信息:\n")
    _print_kv([
        ("store_home", str(config.get_store_home())),
        ("store_dir", str(config.get_store_dir())),
        ("manifest", str(config.get_manifest_path())),
        ("backups", str(config.get_backup_dir())),
        ("config", str(config.get_config_path())),
        ("env override", os.environ.get(config.ENV_STORE_HOME, "(未设置)")),
    ])
    items = store.list_store_skills()
    print(f"\n  共 {len(items)} 个 skill 在中央仓库中")
    return 0


# ===========================================================================
# status
# ===========================================================================

def cmd_status(args) -> int:
    config.ensure_initialized()
    name = args.name
    if store.has_skill(name):
        skill_path = store.get_skill_path(name)
    else:
        # 尝试从工具目录找一个
        skill_path = None
        for d in tools.detect_skill_dirs():
            p = d["path"] / name
            if (p / "SKILL.md").exists():
                skill_path = p.resolve() if p.is_symlink() else p
                break
        if skill_path is None:
            print(f"❌ 未找到 skill: {name}", file=sys.stderr)
            return 1

    cwd = _scope_cwd(args) if args.scope in ("project", "all") else None
    if args.scope == "all":
        scopes_to_show = ["global", "project"]
    elif args.scope == "project":
        scopes_to_show = ["project"]
    else:
        scopes_to_show = ["global"]

    print(f"\n📊 {name} (v{tools.get_skill_version(skill_path)})")
    print(f"   源路径: {skill_path}")
    if "project" in scopes_to_show:
        print(f"   project cwd: {cwd or Path.cwd()}")
    print()
    print(f"  | 工具 | scope | 状态 | 链接类型 | 说明 |")
    print(f"  |------|-------|------|----------|------|")

    icon_map = {
        linker.LINK_STATUS_LINKED: "✅",
        linker.LINK_STATUS_OTHER_SOURCE: "❌",
        linker.LINK_STATUS_REAL_DIR: "⚠️",
        linker.LINK_STATUS_NOT_LINKED: "-",
        linker.LINK_STATUS_TOOL_MISSING: "·",
    }

    for tk in tools.list_tool_keys():
        for sc in scopes_to_show:
            sc_cwd = cwd if sc == "project" else None
            st = linker.get_link_status(skill_path, tk, scope=sc, cwd=sc_cwd)
            icon = icon_map.get(st["status"], "?")
            lt = st.get("link_type") or "-"
            print(f"  | {tools.get_tool_name(tk)} | {sc} | {icon} | {lt} | {st['note']} |")
    return 0


# ===========================================================================
# argparse 入口
# ===========================================================================

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skillctl",
        description="本地 Skill 中央仓库管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sp = p.add_subparsers(dest="command", required=True)

    # install
    pi = sp.add_parser("install", help="从 local/git/private-npm/url 安装 skill；source 为 .txt 时按 skills.txt 批量安装")
    pi.add_argument("source", help="源地址：本地路径 / git URL / @scope/pkg / http(s)://*.zip / *.txt")
    pi.add_argument("--name", help="自定义 skill 名（默认取目录名）")
    pi.add_argument("--type", choices=["local", "git", "private-npm", "url"], help="显式指定来源类型")
    pi.add_argument("--ref", help="git: 分支/tag/commit")
    pi.add_argument("--targets", help="只链接到指定工具，逗号分隔（默认全部）")
    pi.add_argument("--force", action="store_true", help="覆盖中央仓库已存在的同名 skill")
    pi.add_argument("--scope", choices=["global", "project", "both"], default="global",
                    help="链接范围：global=用户级，project=项目级，both=两者（默认 global）")
    pi.add_argument("--cwd", help="project scope 时的项目根（默认 $PWD）")
    pi.add_argument("--copy", action="store_true", help="强制使用复制（覆盖 link_strategy）")
    pi.add_argument("--symlink", action="store_true", help="强制使用 symlink（覆盖 link_strategy）")
    pi.add_argument("--auto-link", action="store_true", help="批量安装时自动链接到工具目录")
    pi.add_argument("--dry-run", action="store_true")
    pi.set_defaults(func=cmd_install)

    # uninstall
    pu = sp.add_parser("uninstall", help="卸载 skill 并清理软链")
    pu.add_argument("name")
    pu.add_argument("--keep-store", action="store_true", help="只解除软链，保留中央仓库实体")
    pu.add_argument("--dry-run", action="store_true")
    pu.set_defaults(func=cmd_uninstall)

    # update
    pup = sp.add_parser("update", help="按 manifest 中记录的来源重新拉取最新版本")
    pup.add_argument("name")
    pup.set_defaults(func=cmd_update)

    # adopt
    pa = sp.add_parser("adopt", help="反向归集：把工具目录已有 skill 收编到中央仓库")
    pa.add_argument("--all", action="store_true", help="批量归集所有真实 skill 目录")
    pa.add_argument("--tool", help="tool_key（单独归集时必需，或与 --all 配合过滤）")
    pa.add_argument("--name", help="skill 名（单独归集时必需）")
    pa.add_argument("--no-backup", action="store_true", help="不备份原目录（默认会备份）")
    pa.add_argument("--no-relink", action="store_true", help="只在原工具建链，不分发到其他工具")
    pa.add_argument("--overwrite", action="store_true", help="若中央仓库已有同名则覆盖")
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--json", action="store_true")
    pa.set_defaults(func=cmd_adopt)

    # list
    pl = sp.add_parser("list", help="列出中央仓库中的 skill；--tools 列各工具中的 skill")
    pl.add_argument("--tools", action="store_true", help="改为列出各 AI 工具目录下的 skill")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_list)

    # link / unlink
    plk = sp.add_parser("link", help="把中央仓库 skill 链接到指定工具")
    plk.add_argument("name")
    plk.add_argument("--targets", help="逗号分隔的 tool_key 列表（默认全部）")
    plk.add_argument("--scope", choices=["global", "project", "both"], default="global",
                     help="链接范围（默认 global）")
    plk.add_argument("--cwd", help="project scope 时的项目根（默认 $PWD）")
    plk.add_argument("--copy", action="store_true", help="强制使用复制")
    plk.add_argument("--symlink", action="store_true", help="强制使用 symlink")
    plk.add_argument("--dry-run", action="store_true")
    plk.set_defaults(func=cmd_link)

    pulk = sp.add_parser("unlink", help="从工具中移除链接（不删除中央仓库内容）")
    pulk.add_argument("name")
    pulk.add_argument("--targets", help="逗号分隔的 tool_key 列表（默认全部）")
    pulk.add_argument("--scope", choices=["global", "project", "both"], default="global",
                     help="解除范围（默认 global）")
    pulk.add_argument("--cwd", help="project scope 时的项目根（默认 $PWD）")
    pulk.add_argument("--dry-run", action="store_true")
    pulk.set_defaults(func=cmd_unlink)

    # export（从 manifest 导出 skills.txt）
    pex = sp.add_parser("export", help="从 manifest 导出 skills.txt（pip requirements 风格）")
    pex.add_argument("--output", "-o", help="输出文件路径（不传则打印到 stdout）")
    pex.add_argument("--no-comments", action="store_true", help="不输出版本/类型注释")
    pex.set_defaults(func=cmd_export)

    # sync（按 skill 名或 skills.txt 链接到工具，不下载）
    psy = sp.add_parser("sync", help="把 skill 链接到工具目录；target 为 .txt 时按 skills.txt 批量")
    psy.add_argument("target", help="skill 名 或 skills.txt 路径")
    psy.add_argument("--targets", help="逗号分隔的 tool_key 列表（默认全部）")
    psy.add_argument("--scope", choices=["global", "project", "both"], default="global",
                     help="链接范围（默认 global）")
    psy.add_argument("--cwd", help="project scope 时的项目根（默认 $PWD）")
    psy.add_argument("--copy", action="store_true", help="强制使用复制")
    psy.add_argument("--symlink", action="store_true", help="强制使用 symlink")
    psy.add_argument("--dry-run", action="store_true")
    psy.set_defaults(func=cmd_sync)

    # detect
    pd = sp.add_parser("detect", help="检测本机已安装的 AI 工具")
    pd.add_argument("--json", action="store_true")
    pd.set_defaults(func=cmd_detect)

    # scan（通用扫描）
    psc = sp.add_parser("scan", help="通用扫描：发现本机所有 skills 目录（含未知工具）")
    psc.add_argument("--max-depth", type=int, default=4, help="从 ~ 起算的最大深度（默认 4）")
    psc.add_argument("--include-empty", action="store_true",
                     help="包含没有任何 skill 子目录的空 skills 目录")
    psc.add_argument("--refresh", action="store_true", help="强制刷新扫描缓存")
    psc.add_argument("--json", action="store_true")
    psc.set_defaults(func=cmd_scan)

    # store
    pst = sp.add_parser("store", help="查看/设置中央仓库根路径")
    pst.add_argument("--set", help="设置新的 store_home（仅修改配置，不迁移数据）")
    pst.set_defaults(func=cmd_store)

    # status
    psts = sp.add_parser("status", help="查看 skill 在各工具中的链接状态")
    psts.add_argument("name")
    psts.add_argument("--scope", choices=["global", "project", "all"], default="global",
                      help="查看范围：global / project / all（默认 global）")
    psts.add_argument("--cwd", help="project scope 时的项目根（默认 $PWD）")
    psts.set_defaults(func=cmd_status)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
