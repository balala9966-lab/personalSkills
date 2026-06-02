"""
多源安装器

支持的来源：
- local:        本地路径（拷贝/移动）
- git:          git clone
- private-npm:  私有 npm 包安装（运行时优先私有 npm 客户端，回退 'npm'）
- url:          下载 zip / tar.gz 并解压

每个 install_from_xxx 函数返回 (skill_dir, version, source_ref)，
由调用方再通过 store.add_skill_from_path() 加入中央仓库。
"""

import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from .tools import expand_path, get_skill_version, is_valid_skill_dir


# ---------------------------------------------------------------------------
# 来源类型识别
# ---------------------------------------------------------------------------

GIT_URL_RE = re.compile(r"^(https?://|git@|ssh://|git://)|\.git($|/)")
NPM_PKG_RE = re.compile(r"^(@[a-z0-9][\w.-]*/)?[a-z0-9][\w.-]*$", re.IGNORECASE)


def detect_source_type(source: str) -> str:
    """
    根据输入字符串智能识别来源类型。

    Returns:
        'local' | 'git' | 'private-npm' | 'url' | 'unknown'
    """
    s = source.strip()

    # 1. 本地路径
    p = expand_path(s)
    if p.exists():
        return "local"

    # 2. URL（zip/tar 后缀）
    if s.startswith(("http://", "https://")) and re.search(r"\.(zip|tar\.gz|tgz|tar)(\?|$)", s):
        return "url"

    # 3. Git
    if GIT_URL_RE.search(s):
        return "git"

    # 4. private-npm 包名（@scope/name 格式）
    if NPM_PKG_RE.match(s):
        return "private-npm"

    # 5. 普通 http(s) 但无压缩后缀，仍按 url 处理
    if s.startswith(("http://", "https://")):
        return "url"

    return "unknown"


# ---------------------------------------------------------------------------
# 通用辅助
# ---------------------------------------------------------------------------

def _find_skill_root(base: Path) -> Optional[Path]:
    """
    在 base 目录及其子目录中查找包含 SKILL.md 的目录。

    支持以下布局：
    - base/SKILL.md
    - base/<single-subdir>/SKILL.md
    - base/package/SKILL.md   (npm pack 解包后的常见结构)
    """
    if (base / "SKILL.md").exists():
        return base

    pkg = base / "package"
    if (pkg / "SKILL.md").exists():
        return pkg

    for child in base.iterdir():
        if child.is_dir() and (child / "SKILL.md").exists():
            return child

    for child in base.iterdir():
        if child.is_dir():
            for sub in child.iterdir():
                if sub.is_dir() and (sub / "SKILL.md").exists():
                    return sub
    return None


def _read_pkg_name(skill_dir: Path) -> Optional[str]:
    """从 package.json 读取包名（取最后一段，去除 scope）"""
    pkg = skill_dir / "package.json"
    if not pkg.exists():
        return None
    try:
        with open(pkg, "r", encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("name", "")
        if "/" in name:
            name = name.split("/", 1)[1]
        return name or None
    except (json.JSONDecodeError, IOError):
        return None


def _run(cmd, cwd=None) -> subprocess.CompletedProcess:
    """运行外部命令，返回 CompletedProcess（不抛异常）"""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# install_from_local
# ---------------------------------------------------------------------------

def install_from_local(source: str) -> Tuple[Path, str, str]:
    """从本地路径安装。Returns (skill_dir, version, source_ref)"""
    src = expand_path(source)
    if not src.exists():
        raise FileNotFoundError(f"路径不存在: {src}")

    skill_dir = _find_skill_root(src) if src.is_dir() else None
    if skill_dir is None:
        raise ValueError(f"未在 {src} 中找到 SKILL.md")

    return skill_dir, get_skill_version(skill_dir), str(src.resolve())


# ---------------------------------------------------------------------------
# install_from_git
# ---------------------------------------------------------------------------

def install_from_git(source: str, ref: Optional[str] = None) -> Tuple[Path, str, str]:
    """通过 git clone 下载到临时目录"""
    if shutil.which("git") is None:
        raise EnvironmentError("未找到 git 命令，请先安装 git")

    tmp_root = Path(tempfile.mkdtemp(prefix="skill-store-git-"))
    clone_dir = tmp_root / "repo"

    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd += ["--branch", ref]
    cmd += [source, str(clone_dir)]

    cp = _run(cmd)
    if cp.returncode != 0:
        raise RuntimeError(f"git clone 失败: {cp.stderr.strip()}")

    skill_dir = _find_skill_root(clone_dir)
    if skill_dir is None:
        raise ValueError(f"git 仓库中未找到 SKILL.md: {source}")

    return skill_dir, get_skill_version(skill_dir), source


# ---------------------------------------------------------------------------
# install_from_private_npm
# ---------------------------------------------------------------------------

def install_from_private_npm(package: str) -> Tuple[Path, str, str]:
    """通过 npm pack 下载 tarball 并解压到临时目录。

    运行时优先使用私有 npm 客户端（如本机存在），回退到 'npm'。
    """
    pm = "tnpm" if shutil.which("tnpm") else ("npm" if shutil.which("npm") else None)
    if pm is None:
        raise EnvironmentError("未找到 npm 命令；请先安装 npm")

    tmp_root = Path(tempfile.mkdtemp(prefix=f"skill-store-{pm}-"))

    cp = _run([pm, "pack", package], cwd=tmp_root)
    if cp.returncode != 0:
        raise RuntimeError(f"{pm} pack 失败: {cp.stderr.strip()}")

    tgz_files = sorted(tmp_root.glob("*.tgz"))
    if not tgz_files:
        raise RuntimeError(f"{pm} pack 未生成 tarball")
    tgz = tgz_files[-1]

    extract_dir = tmp_root / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tgz, "r:gz") as tf:
        tf.extractall(extract_dir)

    skill_dir = _find_skill_root(extract_dir)
    if skill_dir is None:
        raise ValueError(f"npm 包内未找到 SKILL.md: {package}")

    return skill_dir, get_skill_version(skill_dir), package


# ---------------------------------------------------------------------------
# install_from_url
# ---------------------------------------------------------------------------

def install_from_url(url: str) -> Tuple[Path, str, str]:
    """从 URL 下载 zip/tar.gz 并解压到临时目录"""
    parsed = urllib.parse.urlparse(url)
    fname = Path(parsed.path).name or "download"

    tmp_root = Path(tempfile.mkdtemp(prefix="skill-store-url-"))
    download_path = tmp_root / fname

    try:
        with urllib.request.urlopen(url) as resp, open(download_path, "wb") as f:
            shutil.copyfileobj(resp, f)
    except Exception as e:
        raise RuntimeError(f"下载失败: {e}") from e

    extract_dir = tmp_root / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    name_lower = fname.lower()
    if name_lower.endswith(".zip"):
        with zipfile.ZipFile(download_path, "r") as zf:
            zf.extractall(extract_dir)
    elif name_lower.endswith((".tar.gz", ".tgz")):
        with tarfile.open(download_path, "r:gz") as tf:
            tf.extractall(extract_dir)
    elif name_lower.endswith(".tar"):
        with tarfile.open(download_path, "r") as tf:
            tf.extractall(extract_dir)
    else:
        raise ValueError(f"不支持的压缩格式: {fname}")

    skill_dir = _find_skill_root(extract_dir)
    if skill_dir is None:
        raise ValueError(f"压缩包中未找到 SKILL.md: {url}")

    return skill_dir, get_skill_version(skill_dir), url


# ---------------------------------------------------------------------------
# 高层入口
# ---------------------------------------------------------------------------

def install(
    source: str,
    *,
    source_type: Optional[str] = None,
    git_ref: Optional[str] = None,
) -> Tuple[Path, str, str, str]:
    """
    根据 source 自动识别类型并下载到临时目录。

    Returns:
        (skill_dir, version, source_type, source_ref)
    """
    st = source_type or detect_source_type(source)

    if st == "local":
        d, v, ref = install_from_local(source)
    elif st == "git":
        d, v, ref = install_from_git(source, ref=git_ref)
    elif st == "private-npm":
        d, v, ref = install_from_private_npm(source)
    elif st == "url":
        d, v, ref = install_from_url(source)
    else:
        raise ValueError(
            f"无法识别来源类型: {source}（请显式指定 --type local|git|private-npm|url）"
        )

    if not is_valid_skill_dir(d):
        raise ValueError(f"下载结果不是合法 skill 目录: {d}")

    return d, v, st, ref
