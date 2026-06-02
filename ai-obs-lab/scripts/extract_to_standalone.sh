#!/usr/bin/env bash
# Phase 2: extract ai-obs-lab from personalSkills into its own standalone
# repository at ~/IdeaProjects/ai-obs-lab/, while keeping a symlink in place
# so existing skill registrations (claude/cursor/etc.) continue to work.
#
# This script is intentionally conservative:
#   * git status must be clean (no uncommitted changes anywhere in personalSkills)
#   * destination must not exist
#   * --dry-run prints every action without touching disk or git
#
# Usage:
#   bash scripts/extract_to_standalone.sh --dry-run
#   bash scripts/extract_to_standalone.sh           # real extraction
#   DEST=/custom/path bash scripts/extract_to_standalone.sh --dry-run

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "${HERE}/.." && pwd)"                       # personalSkills/ai-obs-lab
REPO_ROOT="$(cd "${SRC_DIR}/.." && pwd)"                  # personalSkills
DEST_DEFAULT="${HOME}/IdeaProjects/ai-obs-lab"
DEST="${DEST:-${DEST_DEFAULT}}"

DRY=0
for arg in "$@"; do
  case "${arg}" in
    --dry-run|-n) DRY=1 ;;
    -h|--help)
      sed -n '1,30p' "$0"
      exit 0
      ;;
    *) echo "unknown arg: ${arg}" >&2; exit 2 ;;
  esac
done

run() {
  if [[ "${DRY}" -eq 1 ]]; then
    echo "DRY  > $*"
  else
    echo "RUN  > $*"
    eval "$@"
  fi
}

echo "=== extract_to_standalone ==="
echo "SRC : ${SRC_DIR}"
echo "DEST: ${DEST}"
echo "MODE: $([[ ${DRY} -eq 1 ]] && echo dry-run || echo REAL)"
echo

# --- preflight ---
if [[ ! -d "${SRC_DIR}/src/ai_obs_lab" ]]; then
  echo "ERROR: ${SRC_DIR}/src/ai_obs_lab not found; refusing to proceed." >&2
  exit 1
fi
if [[ -e "${DEST}" ]]; then
  echo "ERROR: destination already exists: ${DEST}" >&2
  exit 1
fi

# Check git cleanliness (warn-only in dry-run).
if git -C "${REPO_ROOT}" rev-parse >/dev/null 2>&1; then
  if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]]; then
    msg="git working tree is not clean at ${REPO_ROOT}"
    if [[ "${DRY}" -eq 1 ]]; then
      echo "WARN: ${msg} (would block real run)"
    else
      echo "ERROR: ${msg}; commit or stash first." >&2
      exit 1
    fi
  fi
else
  echo "note: ${REPO_ROOT} is not a git repo; will skip git mv and use plain mv"
fi

# --- plan ---
echo
echo "Plan:"
echo "  1. Move ${SRC_DIR}  ->  ${DEST}"
echo "  2. Create symlink   ${SRC_DIR}  ->  ${DEST}"
echo "  3. cd ${DEST} && git init (if not a git repo)"
echo "  4. Patch pyproject.toml to enable [project.scripts] aolab = ai_obs_lab.cli:main"
echo "  5. Print next-step hints (pip install -e ., git remote add, etc.)"
echo

# --- execute ---
run "mkdir -p \"$(dirname \"${DEST}\")\""

if git -C "${REPO_ROOT}" rev-parse >/dev/null 2>&1 && [[ "${DRY}" -eq 0 ]]; then
  run "git -C \"${REPO_ROOT}\" mv \"$(basename \"${SRC_DIR}\")\" \"${DEST}\""
else
  run "mv \"${SRC_DIR}\" \"${DEST}\""
fi

run "ln -s \"${DEST}\" \"${SRC_DIR}\""

run "cd \"${DEST}\" && (git rev-parse >/dev/null 2>&1 || git init -q)"

# Patch pyproject.toml: uncomment [project.scripts] block.
if [[ "${DRY}" -eq 1 ]]; then
  echo "DRY  > sed -i.bak -E 's/^# \\[project.scripts\\]/[project.scripts]/' ${DEST}/pyproject.toml"
  echo "DRY  > sed -i.bak -E 's/^# aolab = /aolab = /' ${DEST}/pyproject.toml"
else
  sed -i.bak -E 's/^# \[project.scripts\]/[project.scripts]/' "${DEST}/pyproject.toml"
  sed -i.bak -E 's/^# aolab = /aolab = /' "${DEST}/pyproject.toml"
  rm -f "${DEST}/pyproject.toml.bak"
fi

echo
echo "Done."
echo
echo "Next steps:"
echo "  cd ${DEST}"
echo "  pip install -e ."
echo "  aolab version"
echo "  git add -A && git commit -m 'extracted from personalSkills'"
echo "  git remote add origin git@github.com:<your-org>/ai-obs-lab.git"
echo "  git push -u origin main"
echo
echo "The symlink at ${SRC_DIR} -> ${DEST} keeps all existing skill registrations valid."
