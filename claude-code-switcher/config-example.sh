#!/bin/bash
# ============================================================
# Claude Code 双平台切换 - 配置模板
# ============================================================
# 使用方法：
#   1. 复制此文件为 setup.sh
#   2. 填入你的 BASE_URL 和 TOKEN
#   3. bash setup.sh
# ============================================================

# ========================== 👇 在这里填值 ==========================

# 平台1 名称
PROFILE_PLATFORM1_NAME="xx"
# 平台1 API 地址
PROFILE_PLATFORM1_BASE_URL="xxx"
# 平台1 Token
PROFILE_PLATFORM1_AUTH_TOKEN="在这里填你的Token"

# 平台2 名称
PROFILE_PLATFORM2_NAME="xx"
# 平台2 API 地址
PROFILE_PLATFORM2_BASE_URL="xx"
# 平台2 Token
PROFILE_PLATFORM2_AUTH_TOKEN="在这里填你的Token"

# 通用模型配置
DEFAULT_MODEL="GLM-5"
DEFAULT_SMALL_FAST_MODEL="Qwen3-Next-80B-A3B-Instruct"
DEFAULT_HAIKU_MODEL="Qwen3-Next-80B-A3B-Instruct"
DEFAULT_OPUS_MODEL="GLM-5"
DEFAULT_SONNET_MODEL="GLM-5"

# 默认平台（新终端启动时使用哪个）
DEFAULT_PROFILE="xx"  # 可选: 平台1 / 平台2

# ========================== 👆 填值结束 ==========================

# 以下和 setup.sh 完全相同，直接 source 或复制 setup.sh 的逻辑即可
echo "请将此文件复制为 setup.sh 并填入配置值后执行"
echo "  cp config-example.sh setup.sh"
echo "  vim setup.sh  # 填入 token"
echo "  bash setup.sh"