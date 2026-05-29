#!/bin/bash
# ============================================================
# Claude Code 双平台切换配置脚本 v2
# ============================================================
# 用途：在任意 Mac/Linux 机器上一键配置 Claude Code 双平台切换
# 原理：直接修改 ~/.claude/settings.json（环境变量会被 settings.json 覆盖）
# 用法：bash setup.sh
# ============================================================

set -e

# ======================== 配置区 ========================
# 👇 在这里填入你的两套配置，其他机器只需改这里 👇

# 平台1：平台 1
PROFILE_PLATFORM1_NAME="平台 1"
PROFILE_PLATFORM1_BASE_URL="https://your-api-platform-1.com/api/anthropic"
PROFILE_PLATFORM1_AUTH_TOKEN="your_token_here_platform_1"

# 平台2：平台 2
PROFILE_PLATFORM2_NAME="平台 2"
PROFILE_PLATFORM2_BASE_URL="https://your-api-platform-2.com/api/anthropic"
PROFILE_PLATFORM2_AUTH_TOKEN="your_token_here_platform_2"

# 平台 1 模型配置
DEFAULT_MODEL="GLM-5"

# 平台 2 模型配置
PLATFORM2_MODEL="gpt-5.1-codex-max-1204-global"
DEFAULT_SMALL_FAST_MODEL="Qwen3-Next-80B-A3B-Instruct"
DEFAULT_HAIKU_MODEL="Qwen3-Next-80B-A3B-Instruct"
DEFAULT_OPUS_MODEL="GLM-5"
DEFAULT_SONNET_MODEL="GLM-5"

# 默认平台（新终端启动时使用的平台）
DEFAULT_PROFILE="platform1"  # platform1 或 platform2

# ======================== 以下无需修改 ========================

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════╗"
echo "║   Claude Code 双平台切换 v2 - 一键配置脚本   ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# -------------------- 步骤 1: 检查前置依赖 --------------------
echo -e "${YELLOW}[1/5] 检查前置依赖...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未检测到 python3（切换函数依赖 python3 修改 settings.json）${NC}"
    exit 1
fi
echo -e "  ✅ python3 $(python3 --version 2>&1 | cut -d' ' -f2)"

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Node.js，请先安装 Node.js (v18+)${NC}"
    exit 1
fi
echo -e "  ✅ Node.js $(node -v)"

# -------------------- 步骤 2: 安装 Claude Code --------------------
echo -e "${YELLOW}[2/5] 安装 Claude Code...${NC}"

if command -v claude &> /dev/null; then
    CURRENT_VERSION=$(claude --version 2>&1 | head -1)
    echo -e "  ✅ Claude Code 已安装: ${CURRENT_VERSION}"
    read -p "  是否重新安装？(y/N): " reinstall
    if [[ "$reinstall" =~ ^[Yy]$ ]]; then
        npm install -g claude-code --registry=https://registry.npmjs.org
        echo -e "  ✅ 重新安装完成"
    fi
else
    echo -e "  正在安装 claude-code ..."
    npm install -g claude-code --registry=https://registry.npmjs.org
    echo -e "  ✅ 安装完成: $(claude --version 2>&1 | head -1)"
fi

# -------------------- 步骤 3: 生成 settings.json --------------------
echo -e "${YELLOW}[3/5] 配置 settings.json...${NC}"

CLAUDE_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_DIR"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# 根据默认平台选择 token 和 url
if [ "$DEFAULT_PROFILE" = "platform1" ]; then
    DEFAULT_AUTH_TOKEN="$PROFILE_PLATFORM1_AUTH_TOKEN"
    DEFAULT_BASE_URL="$PROFILE_PLATFORM1_BASE_URL"
else
    DEFAULT_AUTH_TOKEN="$PROFILE_PLATFORM2_AUTH_TOKEN"
    DEFAULT_BASE_URL="$PROFILE_PLATFORM2_BASE_URL"
fi

if [ -f "$SETTINGS_FILE" ]; then
    echo -e "  📄 发现已有 settings.json，将保留 hooks/plugins 等配置，仅更新 env"
    python3 -c "
import json

with open('$SETTINGS_FILE', 'r') as f:
    data = json.load(f)

new_env = {
    'ANTHROPIC_AUTH_TOKEN': '$DEFAULT_AUTH_TOKEN',
    'ANTHROPIC_BASE_URL': '$DEFAULT_BASE_URL',
    'ANTHROPIC_MODEL': '$DEFAULT_MODEL',
    'ANTHROPIC_SMALL_FAST_MODEL': '$DEFAULT_SMALL_FAST_MODEL',
    'ANTHROPIC_DEFAULT_HAIKU_MODEL': '$DEFAULT_HAIKU_MODEL',
    'ANTHROPIC_DEFAULT_OPUS_MODEL': '$DEFAULT_OPUS_MODEL',
    'ANTHROPIC_DEFAULT_SONNET_MODEL': '$DEFAULT_SONNET_MODEL',
    'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1'
}

data['env'] = new_env
data.setdefault('skipWebFetchPreflight', True)
# 移除可能冲突的 ANTHROPIC_API_KEY
data['env'].pop('ANTHROPIC_API_KEY', None)

with open('$SETTINGS_FILE', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')

print('  ✅ 已更新 settings.json')
"
else
    cat > "$SETTINGS_FILE" << SETTINGS_EOF
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "$DEFAULT_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL": "$DEFAULT_BASE_URL",
    "ANTHROPIC_MODEL": "$DEFAULT_MODEL",
    "ANTHROPIC_SMALL_FAST_MODEL": "$DEFAULT_SMALL_FAST_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "$DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "$DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "$DEFAULT_SONNET_MODEL",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  },
  "skipWebFetchPreflight": true
}
SETTINGS_EOF
    echo -e "  ✅ 已创建 settings.json"
fi

# -------------------- 步骤 4: 写入 Shell 切换函数 --------------------
echo -e "${YELLOW}[4/5] 配置 Shell 切换函数 (v2: 直接修改 settings.json)...${NC}"

# 检测 shell 配置文件
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.bashrc"
fi

# 移除所有旧版 Claude 切换函数
python3 << PYEOF
with open('$SHELL_RC', 'r') as f:
    content = f.read()

# 移除 v1 标记块
import re
# 匹配 "# === Claude Code 多 Key 切换 ===" 或 "# === Claude Code 双平台切换 ===" (不含 v2)
# 一直到 claude-key-status 函数的 } 结束
v1_pattern = r'\n*# === Claude Code (?:多 Key 切换|双平台切换)(?! v2) ===.*?claude-key-status\(\).*?\n\}'
content = re.sub(v1_pattern, '', content, flags=re.DOTALL)

# 移除 v2 标记块
v2_pattern = r'\n*# === Claude Code 双平台切换 v2 \(直接修改 settings\.json\) ===.*?claude-key-status\(\).*?\n\}'
content = re.sub(v2_pattern, '', content, flags=re.DOTALL)

with open('$SHELL_RC', 'w') as f:
    f.write(content)

print('  ✅ 已清理旧版切换函数')
PYEOF

# 写入新版切换函数
cat >> "$SHELL_RC" << SWITCH_EOF

# === Claude Code 双平台切换 v2 (直接修改 settings.json) ===
# 用法: claude-use-platform2 / claude-use-platform1 / claude-key-status
# ⚠️  原理：Claude Code 的 settings.json env 字段会覆盖 Shell 环境变量
#     所以切换必须直接修改 settings.json，单纯 export 不生效

_CLAUDE_SETTINGS="\$HOME/.claude/settings.json"

_claude_set_env() {
    local name="\$1" token="\$2" url="\$3" model="\$4"
    python3 -c "
import json, sys

with open('\$_CLAUDE_SETTINGS', 'r') as f:
    data = json.load(f)

data['env']['ANTHROPIC_AUTH_TOKEN'] = '\$token'
data['env']['ANTHROPIC_BASE_URL'] = '\$url'
data['env']['ANTHROPIC_MODEL'] = '\$model'
data['env']['ANTHROPIC_DEFAULT_OPUS_MODEL'] = '\$model'
data['env']['ANTHROPIC_DEFAULT_SONNET_MODEL'] = '\$model'
data['env'].pop('ANTHROPIC_API_KEY', None)

with open('\$_CLAUDE_SETTINGS', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')
"
    export ANTHROPIC_AUTH_TOKEN="\$token"
    export ANTHROPIC_BASE_URL="\$url"
    export ANTHROPIC_MODEL="\$model"
    export ANTHROPIC_DEFAULT_OPUS_MODEL="\$model"
    export ANTHROPIC_DEFAULT_SONNET_MODEL="\$model"
    unset ANTHROPIC_API_KEY 2>/dev/null
}

claude-use-platform1() {
    _claude_set_env "平台 1" "$PROFILE_PLATFORM1_AUTH_TOKEN" "$PROFILE_PLATFORM1_BASE_URL" "$DEFAULT_MODEL"
    echo "✅ 已切换到 $PROFILE_PLATFORM1_NAME — 模型: $DEFAULT_MODEL"
    echo "   🌐 $PROFILE_PLATFORM1_BASE_URL"
    echo "   🔑 ${PROFILE_PLATFORM1_AUTH_TOKEN:0:8}...${PROFILE_PLATFORM1_AUTH_TOKEN: -4}"
}

claude-use-platform2() {
    _claude_set_env "平台 2" "$PROFILE_PLATFORM2_AUTH_TOKEN" "$PROFILE_PLATFORM2_BASE_URL" "$PLATFORM2_MODEL"
    echo "✅ 已切换到 $PROFILE_PLATFORM2_NAME — 模型: $PLATFORM2_MODEL"
    echo "   🌐 $PROFILE_PLATFORM2_BASE_URL"
    echo "   🔑 ${PROFILE_PLATFORM2_AUTH_TOKEN:0:8}...${PROFILE_PLATFORM2_AUTH_TOKEN: -4}"
}

claude-key-status() {
    echo "╔══════════════════════════════════════╗"
    echo "║   Claude Code 当前配置               ║"
    echo "╚══════════════════════════════════════╝"
    local token url model
    token=\$(python3 -c "import json; d=json.load(open('\$_CLAUDE_SETTINGS')); print(d.get('env',{}).get('ANTHROPIC_AUTH_TOKEN',''))" 2>/dev/null)
    url=\$(python3 -c "import json; d=json.load(open('\$_CLAUDE_SETTINGS')); print(d.get('env',{}).get('ANTHROPIC_BASE_URL',''))" 2>/dev/null)
    model=\$(python3 -c "import json; d=json.load(open('\$_CLAUDE_SETTINGS')); print(d.get('env',{}).get('ANTHROPIC_MODEL',''))" 2>/dev/null)

    if [ "\$url" = "$PROFILE_PLATFORM2_BASE_URL" ]; then
        echo "🧪 平台: $PROFILE_PLATFORM2_NAME"
    elif [ "\$url" = "$PROFILE_PLATFORM1_BASE_URL" ]; then
        echo "🔬 平台: $PROFILE_PLATFORM1_NAME"
    else
        echo "❓ 平台: \$url"
    fi
    if [ -n "\$token" ]; then
        echo "🔑 AUTH_TOKEN: \${token:0:8}...\${token: -4}"
    fi
    echo "🌐 BASE_URL: \$url"
    echo "🤖 MODEL: \$model"
}
SWITCH_EOF

echo -e "  ✅ 已写入切换函数到 $SHELL_RC"

# -------------------- 步骤 5: 验证 --------------------
echo ""
echo -e "${YELLOW}[5/5] 验证配置...${NC}"

source "$SHELL_RC" 2>/dev/null

echo ""
echo -e "  ${GREEN}settings.json${NC}:  $SETTINGS_FILE"
echo -e "  ${GREEN}Shell 函数${NC}:  $SHELL_RC"
echo ""
echo -e "  切换命令："
echo -e "    ${GREEN}claude-use-platform1${NC}      →  $PROFILE_PLATFORM1_NAME"
echo -e "    ${GREEN}claude-use-platform2${NC}    →  $PROFILE_PLATFORM2_NAME"
echo -e "    ${GREEN}claude-key-status${NC}     →  查看当前配置"
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗"
echo    "║   ✅ 配置完成！                              ║"
echo    "║                                              ║"
echo    "║   新终端窗口中即可使用切换命令                ║"
echo    "║   或执行: source $SHELL_RC"
echo    "╚══════════════════════════════════════════════╝${NC}"