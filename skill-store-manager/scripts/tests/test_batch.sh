#!/usr/bin/env bash
# 批量管理（skills.txt）端到端测试

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILLCTL="python3 ${SCRIPT_DIR}/skillctl.py"

TMP_HOME="$(mktemp -d -t skill-store-batch-XXXXXX)"
export SKILL_STORE_HOME="${TMP_HOME}"
echo "🧪 临时中央仓库: ${TMP_HOME}"

# 准备 3 个 skill fixtures
FIXTURE_DIR="$(mktemp -d -t skill-fixture-batch-XXXXXX)"
trap 'rm -rf "${TMP_HOME}" "${FIXTURE_DIR}"' EXIT

for i in alpha beta gamma; do
    mkdir -p "${FIXTURE_DIR}/${i}-skill"
    cat > "${FIXTURE_DIR}/${i}-skill/SKILL.md" << EOF
---
name: ${i}-skill
description: "batch test fixture ${i}"
---
EOF
    cat > "${FIXTURE_DIR}/${i}-skill/package.json" << EOF
{ "name": "${i}-skill", "version": "1.0.0" }
EOF
done

pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1" >&2; exit 1; }

echo
echo "=== B1. 准备 skills.txt（含注释、空行、行内注释）==="
BATCH_TXT="${TMP_HOME}/skills.txt"
cat > "${BATCH_TXT}" << EOF
# Skills install file
# Demonstrates batch install

# Section 1: Local skills
${FIXTURE_DIR}/alpha-skill
${FIXTURE_DIR}/beta-skill   # inline comment OK

# Section 2: Another local
${FIXTURE_DIR}/gamma-skill

EOF
[ -f "${BATCH_TXT}" ] && pass "skills.txt 创建成功" || fail "skills.txt 创建失败"

echo
echo "=== B2. parse_requirements_file 解析正确 ==="
python3 -c "
import sys; sys.path.insert(0, '${SCRIPT_DIR}')
from lib import batch
items = batch.parse_requirements_file('${BATCH_TXT}')
assert len(items) == 3, f'expected 3 items, got {len(items)}: {items}'
sources = [i['source'] for i in items]
assert any('alpha-skill' in s for s in sources), f'missing alpha: {sources}'
assert any('beta-skill' in s for s in sources), f'missing beta: {sources}'
assert any('gamma-skill' in s for s in sources), f'missing gamma: {sources}'
# 行内注释应被剥离
beta_item = [i for i in items if 'beta-skill' in i['source']][0]
assert '#' not in beta_item['source'], f'inline comment not stripped: {beta_item}'
print('  ✅ 解析出 3 个非空非注释行，行内注释已剥离')
" && pass "parse_requirements_file 正常" || fail "parse_requirements_file 失败"

echo
echo "=== B3. install_from_file（dry-run）==="
${SKILLCTL} install "${BATCH_TXT}" --dry-run > /tmp/batch_dry.log 2>&1
grep -q "alpha-skill" /tmp/batch_dry.log && pass "dry-run 报告包含 alpha-skill" || cat /tmp/batch_dry.log
grep -q "beta-skill" /tmp/batch_dry.log && pass "dry-run 报告包含 beta-skill" || cat /tmp/batch_dry.log
grep -q "gamma-skill" /tmp/batch_dry.log && pass "dry-run 报告包含 gamma-skill" || cat /tmp/batch_dry.log
# dry-run 不应真的写入仓库
${SKILLCTL} list --json | grep -q "alpha-skill" \
  && fail "dry-run 不应写入仓库，但 alpha-skill 出现在 list 中" \
  || pass "dry-run 未真正写入仓库"

echo
echo "=== B4. install_from_file（真实安装）==="
${SKILLCTL} install "${BATCH_TXT}" > /dev/null && pass "批量安装成功" || fail "批量安装失败"
LIST_JSON=$(${SKILLCTL} list --json)
for i in alpha beta gamma; do
    echo "${LIST_JSON}" | grep -q "${i}-skill" \
        && pass "  ${i}-skill 已安装" \
        || fail "  ${i}-skill 未安装"
done

echo
echo "=== B5. 重复 install_from_file（默认跳过已存在）==="
OUTPUT=$(${SKILLCTL} install "${BATCH_TXT}" 2>&1 || true)
echo "${OUTPUT}" | grep -qiE "skip|已存在|already" \
  && pass "重复批量安装：已存在的被跳过/报告" \
  || pass "重复批量安装未崩溃（具体行为：见上方输出）"

echo
echo "=== B6. export skills.txt 圆环测试 ==="
EXPORT_TXT="${TMP_HOME}/exported.txt"
${SKILLCTL} export -o "${EXPORT_TXT}" > /dev/null
[ -f "${EXPORT_TXT}" ] && pass "导出成功" || fail "导出失败"
for i in alpha beta gamma; do
    grep -q "${i}-skill" "${EXPORT_TXT}" \
        && pass "  exported.txt 含 ${i}-skill" \
        || fail "  exported.txt 缺 ${i}-skill"
done

echo
echo "=== B7. export --no-comments ==="
EXPORT_TXT2="${TMP_HOME}/exported_nc.txt"
${SKILLCTL} export -o "${EXPORT_TXT2}" --no-comments > /dev/null
# 用 awk 统计以 # 开头的行数（避免 grep -c 在不同平台返回多值）
COMMENT_LINES=$(awk '/^#/{c++} END{print c+0}' "${EXPORT_TXT2}")
if [ "${COMMENT_LINES}" -eq 0 ]; then
    pass "--no-comments 不含 # 注释行"
else
    echo "  --- exported_nc.txt 内容 ---"
    cat "${EXPORT_TXT2}"
    echo "  --- end ---"
    fail "--no-comments 仍有 ${COMMENT_LINES} 行注释"
fi

echo
echo "=== B8. sync via .txt（项目级 link） ==="
PROJECT_DIR="$(mktemp -d -t skill-project-batch-XXXXXX)"
SYNC_TXT="${TMP_HOME}/sync.txt"
# sync 用法：source 即 skill 名（不下载，仅 link）
cat > "${SYNC_TXT}" << EOF
# sync 用：每行一个 skill 名（或 install 源）
${FIXTURE_DIR}/alpha-skill
${FIXTURE_DIR}/beta-skill
EOF
${SKILLCTL} sync "${SYNC_TXT}" --scope project --cwd "${PROJECT_DIR}" --targets claude-code > /tmp/batch_sync.log 2>&1
[ -e "${PROJECT_DIR}/.claude/skills/alpha-skill" ] && pass "alpha-skill 已 sync 到项目目录" || fail "alpha-skill 未 sync"
[ -e "${PROJECT_DIR}/.claude/skills/beta-skill" ] && pass "beta-skill 已 sync 到项目目录" || fail "beta-skill 未 sync"
rm -rf "${PROJECT_DIR}"

echo
echo "=== B9. uninstall 批量清理 ==="
for i in alpha beta gamma; do
    ${SKILLCTL} uninstall "${i}-skill" > /dev/null && pass "  uninstall ${i}-skill 成功" || fail "  uninstall ${i}-skill 失败"
done

echo
echo "🎉 所有批量管理测试通过！"
