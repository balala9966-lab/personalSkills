#!/usr/bin/env python3
"""
kb_init.py - Knowledge Wiki Initialization Tool

Creates a new Knowledge Wiki with the standard directory structure,
schema files, and optional git/qmd setup.

Usage:
    python3 kb_init.py --name my-kb --root /path/to/kb --description "My knowledge base"
    python3 kb_init.py --name my-kb --root /path/to/kb --git-url git@github.com:org/repo.git
"""

import argparse
import json
import logging
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kb_init")

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR.parent / "templates"

WIKI_SUBDIRS = [
    # Business domain
    "entities",
    "concepts",
    "topics",
    "sources",
    "analyses",
    "maps",
    # Code domain
    "code/architecture",
    "code/modules",
    "code/interfaces",
    "code/data-models",
    "code/flows",
    "code/contracts",
    # Cross-domain
    "changelog",
]

RAW_SUBDIRS = [
    "business/assets",
    "business/web",
    "business/yuque",
    "business/feishu",
    "business/local",
    "code",
]

GRAPH_SUBDIRS = []  # graph/ has no subdirs, files are at root

GITIGNORE_CONTENT = """\
# qmd cache and index
.qmd/
*.qmd-cache

# KB state (contains local metadata)
.kb-state.json
.codewiki-meta.json

# OS files
.DS_Store
Thumbs.db

# Node
node_modules/

# Python
__pycache__/
*.pyc
.venv/
venv/

# Editor
*.swp
*.swo
*~
.idea/
.vscode/

# Temporary
*.tmp
*.bak
"""

KBIGNORE_CONTENT = """\
# Knowledge Wiki ignore rules
# Syntax compatible with .gitignore
# Lines starting with # are comments
# Use ! to negate (re-include)

# Exclude draft sources
# raw/business/yuque/drafts/

# Exclude test files from code analysis
# code:**/*_test.go
# code:**/test/**
# code:**/__tests__/**

# Exclude generated code from analysis
# code:src/generated/**
# code:**/*.pb.go
# code:**/*.generated.ts

# Exclude large binary files
# *.pdf
# *.pptx
"""


def render_claude_md(
    kb_name: str,
    description: str,
    code_repos_section: str = "No code repositories linked yet.",
    adapter_configs: str = "Default adapters enabled: web, youtube, arxiv, rss, jupyter, pptx, csv, local-markdown, local-pdf, local-docx, github, git",
    sync_targets_section: str = "No sync targets configured yet.",
    qmd_section: str = "qmd is not configured. Run `qmd_setup.py` to enable semantic search.",
    domain_context: str = "No domain-specific context configured yet.",
) -> str:
    template_path = TEMPLATES_DIR / "kb-schema-claude.md"
    if not template_path.exists():
        logger.error("Template not found: %s", template_path)
        raise FileNotFoundError(f"Template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    content = content.replace("{kb-name}", kb_name)
    content = content.replace("{kb-description}", description)
    content = content.replace("{code-repos-section}", code_repos_section)
    content = content.replace("{adapter-configs}", adapter_configs)
    content = content.replace("{sync-targets-section}", sync_targets_section)
    content = content.replace("{qmd-commands}", qmd_section)
    content = content.replace("{domain-context}", domain_context)
    return content


def render_kb_state(kb_name: str, kb_root: str, description: str, git_remote: Optional[str] = None) -> dict:
    template_path = TEMPLATES_DIR / "kb-state-template.json"
    if not template_path.exists():
        logger.error("Template not found: %s", template_path)
        raise FileNotFoundError(f"Template not found: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    state["kb_name"] = kb_name
    state["kb_root"] = kb_root
    state["created_at"] = now
    state["last_updated"] = now
    state["description"] = description
    state["storage_type"] = "git" if git_remote else "local"
    state["git_remote"] = git_remote
    state["qmd"]["collection_name"] = kb_name
    state["changelog"] = [
        {
            "timestamp": now,
            "operation": "init",
            "summary": f"Initialized knowledge wiki '{kb_name}'",
            "pages_created": ["wiki/index.md", "wiki/overview.md", "wiki/AGENTS.md"],
            "pages_updated": [],
            "source_id": None,
        }
    ]

    return state


def create_agents_md(kb_name: str, description: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""\
---
title: "{kb_name} Navigation"
type: navigation
created: {now}
updated: {now}
---

# {kb_name} — Quick Navigation

> LLM 导航文件：**先读 README.md**（用户说明书），再读本文件，再按需深入。

## 知识库元信息

- 名称：{kb_name}
- 领域：{description}
- 创建时间：{now}

## 检索策略

| 问题类型 | 推荐路径 |
|----------|----------|
| 查找特定实体/系统 | `wiki/entities/` 目录 |
| 理解概念/模式 | `wiki/concepts/` 目录 |
| 领域全景 | `wiki/topics/` 目录 |
| 代码架构 | `wiki/code/architecture/` |
| 接口/API | `wiki/code/interfaces/_index.md` |
| 数据模型 | `wiki/code/data-models/_index.md` |
| 业务流程 | `wiki/code/flows/` |
| 代码-业务关联 | 搜索 `## Business Context` 或 `## Code Implementation` |
| 查询沉淀 | `wiki/analyses/synthesis-*.md` |
| 知识图谱 | `graph/graph.html`（可视化）或 `graph/graph.json`（数据） |
| 全文搜索（大型KB） | `qmd query "{{question}}"` |

## 目录结构速览

```
wiki/
  entities/     — 实体页（组织、系统、API、渠道）
  concepts/     — 概念页（模式、原则、协议）
  topics/       — 主题页（领域分区 hub）
  sources/      — 每源摘要页
  analyses/     — 查询归档、对比分析、合成页
  maps/         — 关系图谱
  code/         — 代码知识域
    architecture/ — 系统架构文档
    modules/      — 模块索引
    interfaces/   — 接口详细索引
    data-models/  — 数据模型索引
    flows/        — 核心业务流程
    contracts/    — API 合约 & 配置变更
  changelog/    — 统一变更追踪
graph/          — 知识图谱（graph.json + graph.html）
```

## 热点页面

_（摄入后自动填充高频访问页面）_
"""


def create_index_md(kb_name: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""\
---
title: "{kb_name} Index"
type: index
created: {now}
updated: {now}
tags:
  - index
  - navigation
status: active
---

# {kb_name} Index

## Overview
- [[overview]] — 知识库全局总结

## Entities
_No entities yet._

## Concepts
_No concepts yet._

## Topics
_No topics yet._

## Sources
_No sources ingested yet._

## Analyses
_No analyses yet._

## Maps
_No maps yet._

## Code Knowledge
### Architecture
_No architecture pages yet._

### Modules
_No module index yet._

### Interfaces
_No interface index yet._

### Data Models
_No data model index yet._

### Flows
_No flow pages yet._

### Contracts
_No contract pages yet._

## Changelog
_No changelog entries yet._
"""


def create_overview_md(kb_name: str, description: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""\
---
title: "{kb_name} Overview"
type: overview
created: {now}
updated: {now}
tags:
  - overview
confidence: medium
status: draft
scope: "High-level overview of the {kb_name} knowledge base"
---

# {kb_name} Overview

{description}

## Scope

_Define what this knowledge base covers here._

## Key Entities

_List key entities as they are added to the KB._

## Key Concepts

_List key concepts as they are added to the KB._

## Code Architecture

_Summary of registered code repositories and their architectures._

## Getting Started

1. Ingest source documents into `raw/`
2. Create wiki pages from sources
3. Build cross-references between pages
4. Use `qmd query` for semantic search (if configured)
"""


def create_log_md(kb_name: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""\
# {kb_name} Activity Log

| Timestamp | Operation | Summary |
|-----------|-----------|---------|
| {now} | init | Knowledge wiki initialized |
"""


def create_readme_md(kb_name: str, description: str) -> str:
    return f"""\
# {kb_name}

## 这是什么？

> {description if description else '一段话描述这个知识库的主题和目标。'}
> 例如：一个关于【支付系统架构】的个人知识库，记录支付渠道、结算流程、风控策略的设计与实现。

## 文件夹规则

- `raw/`：原始素材，**永远不要修改或删除**
- `wiki/`：AI 整理的维基，完全由 AI 维护
- `graph/`：知识图谱数据，由 AI 生成
- `.schema/`：配置文件，用户和 AI 共同维护

## 维基整理规则

- 每个主题一个 .md 文件，放在对应目录（entities/、concepts/、topics/）
- 开头写 YAML frontmatter，包含 title、type、tags、updated
- 用 [[topic-name]] 链接相关主题
- 维护 wiki/index.md 索引
- 添加新素材时，更新相关维基页面

## 重点关注方向

1. 【方向1：请填写你重点关注的领域或主题】
2. 【方向2：请填写你重点关注的领域或主题】
3. 【方向3：请填写你重点关注的领域或主题】

## 源保留偏好

- 重要业务文档：local 保留（完整保存到 raw/）
- 公开网页/视频：link 保留（仅保存元数据和链接）

## 关联代码仓库

- 【仓库1 URL】— 简要说明
- 【仓库2 URL】— 简要说明

## 备注

> 任何其他你想让 AI 知道的信息。
"""


def create_codewiki_meta() -> dict:
    return {
        "version": "1.0.0",
        "last_full_analysis": None,
        "last_incremental_update": None,
        "repos": {},
        "file_hashes": {},
        "stats": {
            "total_modules": 0,
            "total_interfaces": 0,
            "total_data_models": 0,
            "total_flows": 0,
        },
    }


def setup_git(kb_root: Path, git_url: Optional[str] = None) -> bool:
    try:
        if git_url:
            logger.info("Cloning git repository: %s", git_url)
            temp_dir = kb_root.parent / f".kb-clone-{int(time.time())}"
            result = subprocess.run(
                ["git", "clone", git_url, str(temp_dir)],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                logger.error("Git clone failed: %s", result.stderr)
                return False
            git_dir = temp_dir / ".git"
            if git_dir.exists():
                shutil.move(str(git_dir), str(kb_root / ".git"))
            shutil.rmtree(str(temp_dir), ignore_errors=True)
        else:
            logger.info("Initializing new git repository")
            result = subprocess.run(
                ["git", "init"],
                capture_output=True, text=True, cwd=str(kb_root), timeout=30,
            )
            if result.returncode != 0:
                logger.error("Git init failed: %s", result.stderr)
                return False
        return True
    except FileNotFoundError:
        logger.warning("Git is not installed. Skipping git setup.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Git operation timed out")
        return False


def check_qmd_installed() -> bool:
    try:
        result = subprocess.run(
            ["qmd", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def setup_qmd(kb_root: Path, kb_name: str) -> bool:
    if not check_qmd_installed():
        logger.info("qmd not installed. Skipping qmd setup.")
        return False
    try:
        result = subprocess.run(
            ["qmd", "collection", "add", str(kb_root / "wiki"), "--name", kb_name],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            logger.info("qmd collection '%s' registered", kb_name)
            return True
        else:
            logger.warning("qmd collection registration failed: %s", result.stderr)
            return False
    except subprocess.TimeoutExpired:
        logger.warning("qmd setup timed out")
        return False


def init_kb(
    name: str,
    root: str,
    description: str = "",
    git_url: Optional[str] = None,
    skip_qmd: bool = False,
) -> dict:
    kb_root = Path(root).resolve()
    results = {
        "kb_name": name,
        "kb_root": str(kb_root),
        "created_dirs": [],
        "created_files": [],
        "git_initialized": False,
        "qmd_configured": False,
        "errors": [],
    }

    # Create directory structure
    dirs_to_create = [
        kb_root / "raw",
        kb_root / "wiki",
        kb_root / ".schema",
        kb_root / "graph",
    ]
    for subdir in RAW_SUBDIRS:
        dirs_to_create.append(kb_root / "raw" / subdir)
    for subdir in WIKI_SUBDIRS:
        dirs_to_create.append(kb_root / "wiki" / subdir)

    for dir_path in dirs_to_create:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            results["created_dirs"].append(str(dir_path.relative_to(kb_root)))
        except OSError as e:
            logger.error("Failed to create directory %s: %s", dir_path, e)
            results["errors"].append(str(e))

    # Generate schema files
    schema_files = {
        ".schema/CLAUDE.md": render_claude_md(name, description),
        ".schema/source-adapters.md": "# Source Adapters\n\nDefault adapters enabled: web, local-markdown, local-pdf, local-docx, github, git\n\nCustom adapters can be registered here.\n",
        ".schema/code-repos.md": "# Associated Code Repositories\n\nNo code repositories linked yet.\n",
        ".schema/sync-targets.md": "# Sync Targets\n\nNo sync targets configured yet.\n",
        ".schema/conventions.md": "# Wiki Conventions\n\nSee references/obsidian-conventions.md for detailed conventions.\n",
    }

    for rel_path, content in schema_files.items():
        try:
            file_path = kb_root / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            results["created_files"].append(rel_path)
        except Exception as e:
            results["errors"].append(f"Failed to create {rel_path}: {e}")

    # Generate wiki files
    wiki_files = {
        "wiki/index.md": create_index_md(name),
        "wiki/overview.md": create_overview_md(name, description),
        "wiki/AGENTS.md": create_agents_md(name, description),
        "log.md": create_log_md(name),
        "README.md": create_readme_md(name, description),
    }

    for rel_path, content in wiki_files.items():
        try:
            file_path = kb_root / rel_path
            file_path.write_text(content, encoding="utf-8")
            results["created_files"].append(rel_path)
        except Exception as e:
            results["errors"].append(f"Failed to create {rel_path}: {e}")

    # Generate state files
    try:
        state = render_kb_state(name, str(kb_root), description, git_url)
        state_path = kb_root / ".kb-state.json"
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        results["created_files"].append(".kb-state.json")
    except Exception as e:
        results["errors"].append(f"Failed to create .kb-state.json: {e}")

    try:
        codewiki_meta = create_codewiki_meta()
        codewiki_path = kb_root / ".codewiki-meta.json"
        with open(codewiki_path, "w", encoding="utf-8") as f:
            json.dump(codewiki_meta, f, indent=2, ensure_ascii=False)
        results["created_files"].append(".codewiki-meta.json")
    except Exception as e:
        results["errors"].append(f"Failed to create .codewiki-meta.json: {e}")

    # Generate .gitignore
    try:
        gitignore_path = kb_root / ".gitignore"
        gitignore_path.write_text(GITIGNORE_CONTENT, encoding="utf-8")
        results["created_files"].append(".gitignore")
    except Exception as e:
        results["errors"].append(f"Failed to create .gitignore: {e}")

    # Generate .kbignore
    try:
        kbignore_path = kb_root / ".kbignore"
        kbignore_path.write_text(KBIGNORE_CONTENT, encoding="utf-8")
        results["created_files"].append(".kbignore")
    except Exception as e:
        results["errors"].append(f"Failed to create .kbignore: {e}")

    # Generate initial graph files
    try:
        graph_json = {
            "metadata": {
                "kb_name": name,
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_nodes": 0,
                "total_edges": 0,
                "edge_type_counts": {
                    "EXTRACTED": 0,
                    "INFERRED": 0,
                    "AMBIGUOUS": 0,
                },
            },
            "nodes": [],
            "edges": [],
        }
        graph_path = kb_root / "graph" / "graph.json"
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph_json, f, indent=2, ensure_ascii=False)
        results["created_files"].append("graph/graph.json")
    except Exception as e:
        results["errors"].append(f"Failed to create graph/graph.json: {e}")

    # Git setup
    results["git_initialized"] = setup_git(kb_root, git_url)

    # qmd setup
    if not skip_qmd:
        results["qmd_configured"] = setup_qmd(kb_root, name)
        try:
            state_path = kb_root / ".kb-state.json"
            if state_path.exists():
                with open(state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                state["qmd"]["installed"] = results["qmd_configured"]
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Failed to update qmd status: %s", e)

    return results


def print_summary(results: dict) -> None:
    print("\n" + "=" * 60)
    print(f"  Knowledge Wiki Initialized: {results['kb_name']}")
    print("=" * 60)
    print(f"\n  Root: {results['kb_root']}")
    print(f"\n  Directories created: {len(results['created_dirs'])}")
    for d in results["created_dirs"]:
        print(f"    - {d}/")
    print(f"\n  Files created: {len(results['created_files'])}")
    for f in results["created_files"]:
        print(f"    - {f}")
    print(f"\n  Git: {'Yes' if results['git_initialized'] else 'No'}")
    print(f"  qmd: {'Configured' if results['qmd_configured'] else 'Not configured'}")
    if results["errors"]:
        print(f"\n  Errors ({len(results['errors'])}):")
        for err in results["errors"]:
            print(f"    ! {err}")
    print("\n" + "=" * 60)
    print("  Next steps:")
    print("    1. Ingest source documents: /knowledge-wiki ingest")
    print("    2. Add code repositories: /knowledge-wiki ingest <repo-url>")
    print("    3. Query your knowledge: /knowledge-wiki query <question>")
    print("    4. Run health check: /knowledge-wiki lint")
    print("    5. Explore knowledge gaps: /knowledge-wiki explore")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize a new Knowledge Wiki",
    )
    parser.add_argument("--name", required=True, help="KB name (kebab-case recommended)")
    parser.add_argument("--root", required=True, help="Root directory path")
    parser.add_argument("--description", default="", help="Brief description")
    parser.add_argument("--git-url", default=None, help="Git remote URL (optional)")
    parser.add_argument("--skip-qmd", action="store_true", help="Skip qmd setup")

    args = parser.parse_args()

    try:
        results = init_kb(
            name=args.name,
            root=args.root,
            description=args.description,
            git_url=args.git_url,
            skip_qmd=args.skip_qmd,
        )
        print_summary(results)
        if results["errors"]:
            sys.exit(1)
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()