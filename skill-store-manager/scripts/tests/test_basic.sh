#!/usr/bin/env bash
# 基础冒烟测试：验证 skillctl 主要命令能正常运行
# 使用临时仓库路径，不影响真实 ~/.skill-store

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILLCTL="python3 ${SCRIPT_DIR}/skillctl.py"

# 临时仓库目录
TMP_HOME="$(mktemp -d -t skill-store-test-XXXXXX)"
export SKILL_STORE_HOME="${TMP_HOME}"
echo "🧪 临时中央仓库: ${TMP_HOME}"

# 临时 skill fixture
FIXTURE_DIR="$(mktemp -d -t skill-fixture-XXXXXX)"
trap 'rm -rf "${TMP_HOME}" "${FIXTURE_DIR}"' EXIT

mkdir -p "${FIXTURE_DIR}/demo-skill"
cat > "${FIXTURE_DIR}/demo-skill/SKILL.md" << 'EOF'
---
name: demo-skill
description: "for skillctl test"
---

# Demo
EOF
cat > "${FIXTURE_DIR}/demo-skill/package.json" << 'EOF'
{ "name": "demo-skill", "version": "0.0.1" }
EOF

pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1" >&2; exit 1; }

echo
echo "=== 1. detect ==="
${SKILLCTL} detect --json > /dev/null && pass "detect --json 正常" || fail "detect --json 失败"

echo
echo "=== 2. store --show ==="
${SKILLCTL} store > /dev/null && pass "store 命令正常" || fail "store 命令失败"

echo
echo "=== 3. install (local) ==="
${SKILLCTL} install "${FIXTURE_DIR}/demo-skill" > /dev/null && pass "install local 成功" || fail "install local 失败"

echo
echo "=== 4. list ==="
output=$(${SKILLCTL} list --json)
echo "$output" | grep -q "demo-skill" && pass "list 中包含 demo-skill" || fail "list 缺失 demo-skill"

echo
echo "=== 5. status ==="
${SKILLCTL} status demo-skill > /dev/null && pass "status 正常" || fail "status 失败"

echo
echo "=== 6. install (重复，应该报错) ==="
if ${SKILLCTL} install "${FIXTURE_DIR}/demo-skill" 2>/dev/null; then
  fail "重复 install 未报错"
else
  pass "重复 install 正确报错"
fi

echo
echo "=== 7. install --force (覆盖) ==="
${SKILLCTL} install "${FIXTURE_DIR}/demo-skill" --force > /dev/null && pass "--force 覆盖成功" || fail "--force 覆盖失败"

echo
echo "=== 8. unlink ==="
${SKILLCTL} unlink demo-skill --dry-run > /dev/null && pass "unlink --dry-run 正常" || fail "unlink --dry-run 失败"

echo
echo "=== 9. uninstall ==="
${SKILLCTL} uninstall demo-skill > /dev/null && pass "uninstall 成功" || fail "uninstall 失败"

# 验证已删除
output=$(${SKILLCTL} list --json)
echo "$output" | grep -q "demo-skill" && fail "uninstall 后仍存在 demo-skill" || pass "uninstall 后已不存在"

echo
echo "=== 10. adopt --all --dry-run ==="
${SKILLCTL} adopt --all --dry-run --json > /dev/null && pass "adopt --dry-run 正常" || fail "adopt --dry-run 失败"

echo
echo "=== 11. scan 命令（通用扫描机制）==="
${SKILLCTL} scan --json > /dev/null && pass "scan --json 正常" || fail "scan --json 失败"
${SKILLCTL} scan --refresh --json > /dev/null && pass "scan --refresh 正常" || fail "scan --refresh 失败"

echo
echo "=== 12. 伪 AI 工具自动识别 ==="
# 在临时 HOME 下构造一个全新的"伪 AI 工具"目录，验证通用扫描能否识别
FAKE_HOME="$(mktemp -d -t skill-fake-home-XXXXXX)"
mkdir -p "${FAKE_HOME}/.fake-ai-tool/skills/hello-skill"
cat > "${FAKE_HOME}/.fake-ai-tool/skills/hello-skill/SKILL.md" << 'EOF'
---
name: hello-skill
description: "fixture for fake AI tool"
---
EOF

# 同时构造一个嵌套较深的 (深度=4) 的伪工具
mkdir -p "${FAKE_HOME}/.deep-tool/sub/dir/skills/x-skill"
cat > "${FAKE_HOME}/.deep-tool/sub/dir/skills/x-skill/SKILL.md" << 'EOF'
---
name: x-skill
---
EOF

# 通过 HOME=${FAKE_HOME} 让扫描器只看到我们造的伪工具
scan_output=$(HOME="${FAKE_HOME}" ${SKILLCTL} scan --refresh --json)

echo "$scan_output" | grep -q "fake-ai-tool" \
  && pass "通用扫描识别到 .fake-ai-tool（推断 tool_key=fake-ai-tool）" \
  || fail "通用扫描未识别 .fake-ai-tool。原始输出: $scan_output"

echo "$scan_output" | grep -q "deep-tool-sub-dir" \
  && pass "深度=4 的嵌套工具识别为 deep-tool-sub-dir" \
  || fail "深度=4 嵌套工具未识别。原始输出: $scan_output"

# 再造一个空 skills 目录（无任何 SKILL.md），默认应被忽略
mkdir -p "${FAKE_HOME}/.empty-tool/skills"
scan_output2=$(HOME="${FAKE_HOME}" ${SKILLCTL} scan --refresh --json)
echo "$scan_output2" | grep -q "empty-tool" \
  && fail "默认模式下不应识别空 skills 目录，但识别到了 empty-tool" \
  || pass "默认模式正确忽略空 skills 目录"

# 加 --include-empty 后应识别
scan_output3=$(HOME="${FAKE_HOME}" ${SKILLCTL} scan --refresh --include-empty --json)
echo "$scan_output3" | grep -q "empty-tool" \
  && pass "--include-empty 模式下识别空 skills 目录" \
  || fail "--include-empty 未识别空 skills 目录"

rm -rf "${FAKE_HOME}"

echo
echo "=== 13. export skills.txt ==="
# 装个 skill 才能导出
${SKILLCTL} install "${FIXTURE_DIR}/demo-skill" > /dev/null
EXPORT_TXT="${TMP_HOME}/exported.txt"
${SKILLCTL} export -o "${EXPORT_TXT}" > /dev/null && pass "export -o 成功" || fail "export -o 失败"
[ -f "${EXPORT_TXT}" ] && pass "skills.txt 已生成" || fail "skills.txt 未生成"
grep -q "demo-skill" "${EXPORT_TXT}" && pass "skills.txt 含 demo-skill" || fail "skills.txt 缺 demo-skill"
# 测试 stdout
${SKILLCTL} export 2>/dev/null | grep -q "demo-skill" && pass "export stdout 含 demo-skill" || fail "export stdout 缺失"
# 卸载，准备下一个 case 复用
${SKILLCTL} uninstall demo-skill > /dev/null

echo
echo "=== 14. install via .txt ==="
# 准备一个 skills.txt，含注释和空行
BATCH_TXT="${TMP_HOME}/batch.txt"
cat > "${BATCH_TXT}" << EOF
# This is a batch install file
# Format: pip requirements.txt style

${FIXTURE_DIR}/demo-skill  # inline comment
EOF
${SKILLCTL} install "${BATCH_TXT}" > /dev/null && pass "install via .txt 成功" || fail "install via .txt 失败"
${SKILLCTL} list --json | grep -q "demo-skill" && pass "批量安装后 list 含 demo-skill" || fail "批量安装后 list 缺失"
# dry-run 应不报错
${SKILLCTL} install "${BATCH_TXT}" --dry-run > /dev/null && pass "install via .txt --dry-run 正常" || fail "dry-run 失败"

echo
echo "=== 15. project scope link/unlink ==="
PROJECT_DIR="$(mktemp -d -t skill-project-XXXXXX)"
# 在项目目录下，link 到 project scope（默认会把 skill 链接到 PROJECT_DIR/.claude/skills/ 等）
${SKILLCTL} link demo-skill --scope project --cwd "${PROJECT_DIR}" --targets claude-code > /dev/null \
  && pass "project scope link 成功" || fail "project scope link 失败"
# 验证 PROJECT_DIR 下确实出现了软链接（或目录）
ls "${PROJECT_DIR}/.claude/skills/demo-skill/SKILL.md" >/dev/null 2>&1 \
  && pass "项目级 .claude/skills/demo-skill/SKILL.md 存在" || fail "项目级链接未创建"
# status 看 project scope
${SKILLCTL} status demo-skill --scope project --cwd "${PROJECT_DIR}" > /dev/null \
  && pass "status --scope project 正常" || fail "status --scope project 失败"
# all scope
${SKILLCTL} status demo-skill --scope all --cwd "${PROJECT_DIR}" > /dev/null \
  && pass "status --scope all 正常" || fail "status --scope all 失败"
# unlink
${SKILLCTL} unlink demo-skill --scope project --cwd "${PROJECT_DIR}" --targets claude-code > /dev/null \
  && pass "project scope unlink 成功" || fail "project scope unlink 失败"
ls "${PROJECT_DIR}/.claude/skills/demo-skill" >/dev/null 2>&1 \
  && fail "unlink 后项目级链接仍存在" || pass "unlink 后项目级链接已移除"
rm -rf "${PROJECT_DIR}"

echo
echo "=== 16. --copy 强制复制 ==="
PROJECT_DIR2="$(mktemp -d -t skill-project2-XXXXXX)"
${SKILLCTL} link demo-skill --scope project --cwd "${PROJECT_DIR2}" --targets claude-code --copy > /dev/null \
  && pass "--copy link 成功" || fail "--copy link 失败"
LINKED_PATH="${PROJECT_DIR2}/.claude/skills/demo-skill"
[ -e "${LINKED_PATH}" ] && pass "--copy 目标存在" || fail "--copy 目标缺失"
[ -L "${LINKED_PATH}" ] \
  && fail "--copy 不应该创建软链接，但创建了" \
  || pass "--copy 创建的是真实目录而非软链接"
# 验证内容是真实复制
[ -f "${LINKED_PATH}/SKILL.md" ] && pass "--copy SKILL.md 已复制" || fail "--copy SKILL.md 缺失"
${SKILLCTL} unlink demo-skill --scope project --cwd "${PROJECT_DIR2}" --targets claude-code > /dev/null
rm -rf "${PROJECT_DIR2}"

echo
echo "=== 17. manifest schema v2.0 → v2.1 自动升级 ==="
# 读 manifest，确认 version 是 2.1，且 linked_targets 是 dict 列表
MANIFEST="${TMP_HOME}/manifest.json"
[ -f "${MANIFEST}" ] && pass "manifest 文件存在" || fail "manifest 文件缺失"
python3 -c "
import json, sys
with open('${MANIFEST}') as f:
    m = json.load(f)
assert m.get('version') == '2.1', f\"version expected 2.1, got {m.get('version')}\"
print('  ✅ manifest version=2.1')
demo = m.get('skills', {}).get('demo-skill', {})
targets = demo.get('linked_targets', [])
print(f'  ✅ linked_targets has {len(targets)} entries')
for t in targets:
    assert isinstance(t, dict), f'expected dict, got {type(t).__name__}: {t!r}'
    assert 'tool_key' in t, f'missing tool_key: {t}'
    assert 'scope' in t, f'missing scope: {t}'
    assert 'link_type' in t, f'missing link_type: {t}'
print('  ✅ linked_targets 全部为 dict 形态')
" && pass "schema v2.1 校验通过" || fail "schema v2.1 校验失败"

# 模拟旧 schema：手工写一个 v2.0 风格的 manifest，再调任一命令，应自动升级
LEGACY_MANIFEST="${TMP_HOME}/legacy_manifest.json"
cat > "${LEGACY_MANIFEST}" << 'EOF'
{
  "version": "2.0",
  "skills": {
    "legacy-skill": {
      "name": "legacy-skill",
      "version": "1.0.0",
      "linked_targets": ["claude-code", "cursor"]
    }
  }
}
EOF
python3 -c "
import sys; sys.path.insert(0, '${SCRIPT_DIR}')
from lib import manifest as m
m.MANIFEST_PATH = None  # 让 _path() 走 config 默认
import os
os.environ['SKILL_STORE_HOME'] = '${TMP_HOME}'
# 直接调用 _normalize_targets 测试兼容
norm = m._normalize_targets(['claude-code', 'cursor'])
assert len(norm) == 2
assert norm[0]['tool_key'] == 'claude-code'
assert norm[0]['scope'] == 'global'
assert norm[0]['link_type'] == 'symlink'
print('  ✅ _normalize_targets 兼容 [str] 旧格式')
" && pass "schema v2.0 → v2.1 自动归一化" || fail "归一化失败"

echo
echo "🎉 所有冒烟测试通过！"
