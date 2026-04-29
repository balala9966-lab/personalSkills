"""
中央仓库 manifest 元数据管理 (schema v2.1)

manifest.json 结构（v2.1）：
{
  "version": "2.1",
  "store_path": "/Users/xxx/.skill-store/store",
  "skills": {
    "skill-name": {
      "version": "1.0.0",
      "source": {"type": "git|private-npm|local|url|adopted", "ref": "..."},
      "installed_at": "2026-04-28T12:00:00Z",
      "updated_at": "2026-04-28T12:00:00Z",
      "linked_targets": [
        {"tool_key": "claude-code", "scope": "global", "link_type": "symlink"},
        {"tool_key": "claude-code", "scope": "project", "link_type": "symlink",
         "project_root": "/Users/xxx/IdeaProjects/foo"}
      ]
    }
  }
}

兼容性：
- 旧格式 linked_targets: ["claude-code", "codex-cli"] 由 load_manifest() 自动归一化
  为 dict 形态（默认 scope=global, link_type=symlink）
- 升级触发时机：load_manifest() 读取后；下次 save 时持久化新格式
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from .config import get_manifest_path, get_store_dir

MANIFEST_VERSION = "2.1"
DEFAULT_SCOPE = "global"
DEFAULT_LINK_TYPE = "symlink"

# ---------------------------------------------------------------------------
# 时间工具
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """返回 UTC ISO8601 时间戳，以 Z 结尾"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# ---------------------------------------------------------------------------
# linked_targets 形态归一化（v2.0 → v2.1 兼容）
# ---------------------------------------------------------------------------

def _normalize_target_entry(entry) -> Optional[Dict]:
    """
    把单条 linked_target 归一化成 dict：
    - "claude-code" → {tool_key, scope=global, link_type=symlink}
    - {tool_key, scope?, link_type?, project_root?} → 补齐默认值
    无法识别返回 None。
    """
    if isinstance(entry, str):
        if not entry:
            return None
        return {
            "tool_key": entry,
            "scope": DEFAULT_SCOPE,
            "link_type": DEFAULT_LINK_TYPE,
        }
    if isinstance(entry, dict):
        tk = entry.get("tool_key")
        if not tk:
            return None
        out = {
            "tool_key": tk,
            "scope": entry.get("scope") or DEFAULT_SCOPE,
            "link_type": entry.get("link_type") or DEFAULT_LINK_TYPE,
        }
        if entry.get("project_root"):
            out["project_root"] = entry["project_root"]
        return out
    return None

def _normalize_targets(raw) -> List[Dict]:
    """把任意形态的 linked_targets（[str] 或 [dict]）统一成 dict 列表"""
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    result: List[Dict] = []
    seen = set()  # 去重 key
    for item in raw:
        norm = _normalize_target_entry(item)
        if norm is None:
            continue
        key = (norm["tool_key"], norm["scope"], norm.get("project_root", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(norm)
    return result

def _target_matches(entry: Dict, tool_key: str, scope: str = DEFAULT_SCOPE,
                    project_root: Optional[str] = None) -> bool:
    """判断一条 dict 形态的 target 是否匹配指定 (tool_key, scope, project_root)"""
    if entry.get("tool_key") != tool_key:
        return False
    if (entry.get("scope") or DEFAULT_SCOPE) != scope:
        return False
    if scope == "project":
        return (entry.get("project_root") or None) == (project_root or None)
    return True

def _sort_targets(targets: List[Dict]) -> List[Dict]:
    """按 tool_key, scope, project_root 排序，便于 diff 与稳定输出"""
    return sorted(
        targets,
        key=lambda t: (t.get("tool_key", ""), t.get("scope", ""),
                       t.get("project_root", "")),
    )

# ---------------------------------------------------------------------------
# source.type 归一化（v2.0 → v2.1 兼容：旧 'tnpm' → 'private-npm'）
# ---------------------------------------------------------------------------

# 兼容映射表：把已废弃/非通用的 source.type 值归一化成对外通用名
_SOURCE_TYPE_ALIASES = {
    "tnpm": "private-npm",
}

def _normalize_source(source) -> Optional[Dict]:
    """归一化 skill.source 字段：
    - 把已废弃的 type 值（如 'tnpm'）映射为通用名（'private-npm'）
    - 非 dict 输入返回 None
    """
    if not isinstance(source, dict):
        return None
    t = source.get("type")
    if t in _SOURCE_TYPE_ALIASES:
        return {**source, "type": _SOURCE_TYPE_ALIASES[t]}
    return source

# ---------------------------------------------------------------------------
# 读写
# ---------------------------------------------------------------------------

def load_manifest() -> Dict:
    """加载 manifest，不存在则返回空骨架；自动归一化 linked_targets"""
    path = get_manifest_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "version" not in data:
                data = {
                    "version": MANIFEST_VERSION,
                    "store_path": str(get_store_dir()),
                    "skills": data.get("skills", {}),
                }
            # v2.0 → v2.1：归一化 linked_targets + source.type 兼容
            skills = data.get("skills") or {}
            for _name, entry in skills.items():
                if not isinstance(entry, dict):
                    continue
                if "linked_targets" in entry:
                    entry["linked_targets"] = _normalize_targets(
                        entry.get("linked_targets") or []
                    )
                if "source" in entry:
                    norm_src = _normalize_source(entry.get("source"))
                    if norm_src is not None:
                        entry["source"] = norm_src
            data["version"] = MANIFEST_VERSION
            return data
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "version": MANIFEST_VERSION,
        "store_path": str(get_store_dir()),
        "skills": {},
    }

def save_manifest(manifest: Dict) -> None:
    path = get_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# Skill 条目操作
# ---------------------------------------------------------------------------

def add_skill_entry(
    name: str,
    version: str,
    source_type: str,
    source_ref: str,
    linked_targets: Optional[List[Union[str, Dict]]] = None,
) -> Dict:
    """
    新增/更新一条 skill 记录，返回该条记录。
    linked_targets 既支持旧的 [str]（自动转 global/symlink），也支持新的 [dict]。
    """
    manifest = load_manifest()
    now = _now_iso()
    existing = manifest["skills"].get(name)

    if existing:
        existing["version"] = version
        existing["source"] = {"type": source_type, "ref": source_ref}
        existing["updated_at"] = now
        if linked_targets is not None:
            existing["linked_targets"] = _normalize_targets(linked_targets)
        entry = existing
    else:
        entry = {
            "version": version,
            "source": {"type": source_type, "ref": source_ref},
            "installed_at": now,
            "updated_at": now,
            "linked_targets": _normalize_targets(linked_targets or []),
        }
        manifest["skills"][name] = entry

    save_manifest(manifest)
    return entry

def remove_skill_entry(name: str) -> bool:
    manifest = load_manifest()
    if name in manifest["skills"]:
        del manifest["skills"][name]
        save_manifest(manifest)
        return True
    return False

def get_skill_entry(name: str) -> Optional[Dict]:
    manifest = load_manifest()
    return manifest["skills"].get(name)

def list_skills() -> Dict[str, Dict]:
    return load_manifest()["skills"]

def update_linked_targets(name: str,
                          linked_targets: List[Union[str, Dict]]) -> bool:
    """整体替换 linked_targets；输入支持 [str] 或 [dict]"""
    manifest = load_manifest()
    if name not in manifest["skills"]:
        return False
    norm = _normalize_targets(linked_targets)
    manifest["skills"][name]["linked_targets"] = _sort_targets(norm)
    manifest["skills"][name]["updated_at"] = _now_iso()
    save_manifest(manifest)
    return True

def add_linked_target(name: str,
                       target: Union[str, Dict, None] = None,
                       *,
                       tool_key: Optional[str] = None,
                       scope: str = DEFAULT_SCOPE,
                       link_type: str = DEFAULT_LINK_TYPE,
                       project_root: Optional[str] = None) -> bool:
    """
    新增一条链接记录。两种调用方式：
      1) add_linked_target(name, "claude-code")  # 旧 API，自动 global/symlink
      2) add_linked_target(name, tool_key="claude-code", scope="project",
                           link_type="copy", project_root="/path")
    已存在的同 (tool_key, scope, project_root) 记录会被更新（link_type 覆盖）。
    """
    manifest = load_manifest()
    if name not in manifest["skills"]:
        return False

    if target is not None:
        norm = _normalize_target_entry(target)
        if norm is None:
            return False
    else:
        if not tool_key:
            return False
        norm = {"tool_key": tool_key, "scope": scope, "link_type": link_type}
        if project_root and scope == "project":
            norm["project_root"] = project_root

    raw_targets = manifest["skills"][name].get("linked_targets") or []
    targets = _normalize_targets(raw_targets)

    found = False
    for i, t in enumerate(targets):
        if _target_matches(t, norm["tool_key"],
                            norm.get("scope", DEFAULT_SCOPE),
                            norm.get("project_root")):
            targets[i] = norm
            found = True
            break
    if not found:
        targets.append(norm)

    manifest["skills"][name]["linked_targets"] = _sort_targets(targets)
    manifest["skills"][name]["updated_at"] = _now_iso()
    save_manifest(manifest)
    return True

def remove_linked_target(name: str,
                          target: Union[str, Dict, None] = None,
                          *,
                          tool_key: Optional[str] = None,
                          scope: str = DEFAULT_SCOPE,
                          project_root: Optional[str] = None) -> bool:
    """
    删除一条链接记录（按 tool_key + scope + project_root 匹配）。
    """
    manifest = load_manifest()
    if name not in manifest["skills"]:
        return False

    if target is not None:
        norm = _normalize_target_entry(target)
        if norm is None:
            return False
        match_tk = norm["tool_key"]
        match_scope = norm.get("scope", DEFAULT_SCOPE)
        match_root = norm.get("project_root")
    else:
        if not tool_key:
            return False
        match_tk, match_scope, match_root = tool_key, scope, project_root

    raw_targets = manifest["skills"][name].get("linked_targets") or []
    targets = _normalize_targets(raw_targets)
    new_targets = [t for t in targets
                   if not _target_matches(t, match_tk, match_scope, match_root)]

    if len(new_targets) == len(targets):
        return False

    manifest["skills"][name]["linked_targets"] = _sort_targets(new_targets)
    manifest["skills"][name]["updated_at"] = _now_iso()
    save_manifest(manifest)
    return True

def get_linked_targets(name: str) -> List[Dict]:
    """读取 skill 的 linked_targets（已归一化为 dict 列表）"""
    entry = get_skill_entry(name)
    if not entry:
        return []
    return _normalize_targets(entry.get("linked_targets") or [])

def touch_updated(name: str) -> None:
    manifest = load_manifest()
    if name in manifest["skills"]:
        manifest["skills"][name]["updated_at"] = _now_iso()
        save_manifest(manifest)
