# ai-obs-lab 无感观测包装层
# ---------------------------------------------------------------------------
# 用法：在 ~/.zshrc 末尾加一行：
#     source /Users/yushu/IdeaProjects/personalSkills/ai-obs-lab/bin/obs.sh
# 然后像平时一样用，只是命令加 -obs 后缀：
#     claude-obs                 # 交互式 Claude Code，全程被观测
#     claude-obs -p "你的问题"    # 单次
#     cfuse-obs                  # 交互式 CodeFuse，全程被观测
#     obs report                 # 打开 HTML 报告
#     obs tail                   # 实时看请求流水
#     obs status / obs stop      # 代理状态 / 停止
#
# 原来的 claude / cfuse 命令完全不受影响。
# ---------------------------------------------------------------------------

# 项目根（这个文件所在目录的上一级）
export AI_OBS_LAB_HOME="$(cd "$(dirname "${(%):-%x}")/.." 2>/dev/null && pwd)"
if [ -z "$AI_OBS_LAB_HOME" ]; then
  # bash 兜底（zsh 用 %x，bash 用 BASH_SOURCE）
  AI_OBS_LAB_HOME="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
fi

AI_OBS_LAB_PROXY="http://127.0.0.1:8788"
AI_OBS_LAB_STATE="${HOME}/.ai-obs-lab"
AI_OBS_LAB_PID="${AI_OBS_LAB_STATE}/proxy.pid"
AI_OBS_LAB_LOG="${AI_OBS_LAB_STATE}/proxy.stderr.log"

# --- 确保代理在运行（不在则后台拉起）---------------------------------------
_obs_ensure_proxy() {
  if curl -s -m 2 "${AI_OBS_LAB_PROXY}/_health" >/dev/null 2>&1; then
    return 0
  fi
  echo "[obs] 代理未运行，正在后台启动…" >&2
  mkdir -p "${AI_OBS_LAB_STATE}"
  (
    cd "${AI_OBS_LAB_HOME}" || exit 1
    PYTHONPATH="${AI_OBS_LAB_HOME}/src" nohup python3 -m ai_obs_lab.cli proxy \
      >>"${AI_OBS_LAB_LOG}" 2>&1 &
    echo $! >"${AI_OBS_LAB_PID}"
  )
  # 等待就绪（最多 5 秒）
  local i=0
  while [ $i -lt 25 ]; do
    if curl -s -m 1 "${AI_OBS_LAB_PROXY}/_health" >/dev/null 2>&1; then
      echo "[obs] 代理已就绪：${AI_OBS_LAB_PROXY}" >&2
      return 0
    fi
    sleep 0.2
    i=$((i + 1))
  done
  echo "[obs] 代理启动失败，请查看日志：${AI_OBS_LAB_LOG}" >&2
  return 1
}

# --- claude-obs：用临时 settings 接管 BASE_URL ------------------------------
# Claude Code 把 ANTHROPIC_BASE_URL 写死在 ~/.claude/settings.json，会覆盖 shell env，
# 所以必须生成一份临时 settings（继承真实 token/model，仅改 BASE_URL 指向代理）。
claude-obs() {
  _obs_ensure_proxy || return 1
  local tmp
  tmp="$(mktemp -t claude-obs.XXXXXX.json)"
  python3 - "$tmp" <<'PYEOF'
import json, os, sys
src = os.path.expanduser("~/.claude/settings.json")
out = sys.argv[1]
data = {}
if os.path.exists(src):
    with open(src) as f:
        data = json.load(f)
env = data.get("env", {})
# 把上游指向代理的 antchat 路由；其余 token / model 原样保留。
env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:8788/upstream/antchat"
data["env"] = env
# 临时配置不带 hooks，避免 SessionStart 等 hook 干扰观测（保持纯净链路）。
data.pop("hooks", None)
with open(out, "w") as f:
    json.dump(data, f)
PYEOF
  echo "[obs] claude 走观测代理（upstream=antchat），trace 落盘到 ~/.ai-obs-lab/logs" >&2
  command claude --settings "$tmp" "$@"
  local rc=$?
  rm -f "$tmp"
  return $rc
}

# --- cfuse-obs：直接用 env 接管（cfuse 读 shell env 的 BASE_URL）-----------
cfuse-obs() {
  _obs_ensure_proxy || return 1
  echo "[obs] cfuse 走观测代理（upstream=cfuse），trace 落盘到 ~/.ai-obs-lab/logs" >&2
  ANTHROPIC_BASE_URL="http://127.0.0.1:8788/upstream/cfuse" command cfuse "$@"
}

# --- obs：辅助子命令（report / tail / status / stop / logs）----------------
obs() {
  local cmd="${1:-status}"
  shift 2>/dev/null
  case "$cmd" in
    report)
      _obs_ensure_proxy
      PYTHONPATH="${AI_OBS_LAB_HOME}/src" python3 -m ai_obs_lab.cli report --date today --open "$@"
      ;;
    tail)
      PYTHONPATH="${AI_OBS_LAB_HOME}/src" python3 -m ai_obs_lab.cli tail "$@"
      ;;
    status)
      if curl -s -m 2 "${AI_OBS_LAB_PROXY}/_health" >/dev/null 2>&1; then
        echo "[obs] 代理运行中：${AI_OBS_LAB_PROXY}"
      else
        echo "[obs] 代理未运行"
      fi
      echo "  log_dir: ~/.ai-obs-lab/logs"
      echo "  home   : ${AI_OBS_LAB_HOME}"
      ;;
    stop)
      if [ -f "${AI_OBS_LAB_PID}" ]; then
        kill "$(cat "${AI_OBS_LAB_PID}")" 2>/dev/null && echo "[obs] 已停止代理"
        rm -f "${AI_OBS_LAB_PID}"
      else
        echo "[obs] 无 pid 文件，代理可能未通过 obs 启动"
      fi
      ;;
    logs)
      tail -n 80 "${AI_OBS_LAB_LOG}" 2>/dev/null || echo "[obs] 暂无日志"
      ;;
    *)
      echo "用法: obs [status|report|tail|stop|logs]" >&2
      echo "工具命令: claude-obs / cfuse-obs（参数与原命令一致）" >&2
      ;;
  esac
}
