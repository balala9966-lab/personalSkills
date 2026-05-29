# Claude Code 双平台切换工具

一键配置 Claude Code 在多个 API 平台之间自由切换。

## 🎯 解决什么问题

Claude Code 只能配置一个 `ANTHROPIC_AUTH_TOKEN` 和 `ANTHROPIC_BASE_URL`，如果你有两套 API，想在不同场景切换使用，原生不支持。

这个工具通过 **直接修改 `settings.json`** 的机制实现一键切换：
- ⚠️ Claude Code 的 `settings.json` 中 `env` 字段会**覆盖** Shell 环境变量
- 所以单纯 `export` 环境变量是不生效的，必须修改 `settings.json`
- 切换函数内调用 python3 修改 `settings.json`，同时 export 环境变量保持一致

## 🏗️ 原理说明

```
Claude Code 配置优先级：

  settings.json 的 env 字段 (最高)  →  Claude Code 启动时读取并设置为进程环境变量
       ↑
  切换函数修改 settings.json        →  claude-use-platform1 / claude-use-platform2
       ↑
  Shell 环境变量 (会被覆盖！)        →  export 不生效 ❌
```

**切换函数做了什么？**
1. 用 python3 修改 `~/.claude/settings.json` 中的 `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL`
2. 同时 `export` 环境变量保持当前终端一致
3. `unset` 掉 `ANTHROPIC_API_KEY` 避免认证方式冲突
4. 全局生效，所有新开的 claude 进程都用新配置

## 🚀 快速使用

### 新机器一键安装

1. 编辑 `setup.sh` 顶部的 **配置区**，填入你的两套 API 地址和 Token
2. 执行：

```bash
bash setup.sh
```

3. 新开终端（或 `source ~/.zshrc`），即可使用：

```bash
claude-use-平台1      # 切换到平台1
claude-use-平台2    # 切换到 平台2
claude-key-status     # 查看当前用的是哪个
```

### 配置区示例

```bash
# 平台1：
PROFILE_PLATFORM1_NAME="平台1"
PROFILE_PLATFORM1_BASE_URL="平台1的API地址"
PROFILE_PLATFORM1_AUTH_TOKEN="你的Token"

# 平台2：
PROFILE_PLATFORM2_NAME="平台2"
PROFILE_PLATFORM2_BASE_URL="平台2的API地址"
PROFILE_PLATFORM2_AUTH_TOKEN="你的Token"

# 默认平台（新终端用哪个）
DEFAULT_PROFILE="平台1"  
```

## 📂 文件结构

```
claude-code-switcher/
├── setup.sh          # 一键安装脚本（核心）
├── README.md         # 本文档
└── config-example.sh # 纯配置模板（只要填值）
```

## 🔧 手动配置（理解原理）

如果不想用脚本，手动配置步骤如下：

### 1. 安装 Claude Code

```bash
npm install -g claude-code --registry=https://registry.npmjs.org
```

### 2. 创建 settings.json

```bash
mkdir -p ~/.claude
cat > ~/.claude/settings.json << 'EOF'
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "你的默认Token",
    "ANTHROPIC_BASE_URL": "https://your-api-platform-1.com/api/anthropic",
    "ANTHROPIC_MODEL": "GLM-5",
    "ANTHROPIC_SMALL_FAST_MODEL": "Qwen3-Next-80B-A3B-Instruct",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "Qwen3-Next-80B-A3B-Instruct",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "GLM-5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "GLM-5",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  },
  "skipWebFetchPreflight": true
}
EOF
```

### 3. 添加切换函数到 ~/.zshrc

```bash
# 切换到平台 1
claude-use-platform1() {
    export ANTHROPIC_AUTH_TOKEN="你的平台 1 Token"
    export ANTHROPIC_BASE_URL="https://your-api-platform-1.com/api/anthropic"
    export ANTHROPIC_MODEL="GLM-5"
    unset ANTHROPIC_API_KEY 2>/dev/null
    echo "✅ 已切换到平台 1"
}

# 切换到平台 2
claude-use-platform2() {
    export ANTHROPIC_AUTH_TOKEN="你的平台 2 Token"
    export ANTHROPIC_BASE_URL="https://your-api-platform-2.com/api/anthropic"
    export ANTHROPIC_MODEL="GLM-5"
    unset ANTHROPIC_API_KEY 2>/dev/null
    echo "✅ 已切换到平台 2"
}

# 查看当前配置
claude-key-status() {
    echo "=== Claude Code 当前配置 ==="
    if [ -n "$ANTHROPIC_AUTH_TOKEN" ]; then
        echo "🔑 AUTH_TOKEN: ${ANTHROPIC_AUTH_TOKEN:0:8}...${ANTHROPIC_AUTH_TOKEN: -4}"
        echo "🌐 BASE_URL: $ANTHROPIC_BASE_URL"
    else
        echo "⚙️  使用 settings.json 默认配置"
    fi
    echo "🤖 MODEL: ${ANTHROPIC_MODEL:-默认}"
}
```

### 4. 生效

```bash
source ~/.zshrc
```

## 💡 进阶技巧

### 多开终端用不同平台

```bash
# 终端1 - 用平台 1
claude-use-platform1
claude

# 终端2 - 用平台 2  
claude-use-platform2
claude
```

### 给某个项目固定平台

在项目目录创建 `.claude/settings.json`（项目级覆盖用户级）：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "这个项目专用的Token",
    "ANTHROPIC_BASE_URL": "https://your-api-platform-2.com/api/anthropic"
  }
}
```

### 临时切换模型

```bash
# 临时用 DeepSeek-R1
export ANTHROPIC_MODEL="DeepSeek-R1"
claude

# 临时用 Kimi
export ANTHROPIC_MODEL="Kimi-K2.5"
claude
```

## ⚠️ 注意事项

- `settings.json` 中 **不要同时** 设置 `ANTHROPIC_AUTH_TOKEN` 和 `ANTHROPIC_API_KEY`，会产生冲突
- 切换函数只影响当前终端，新终端走默认配置
- 如果 Claude Code 版本升级后配置格式有变，需要重新运行 `setup.sh`