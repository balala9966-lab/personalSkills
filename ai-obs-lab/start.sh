#!/usr/bin/env bash
# ai-obs-lab one-shot launcher.
#
# Usage:
#   ./start.sh              # start proxy in background, then live-tail summaries
#   ./start.sh proxy        # foreground proxy (Ctrl-C to stop)
#   ./start.sh tail         # just tail
#   ./start.sh report       # generate today's HTML and `open` it
#   ./start.sh stop         # kill background proxy
#   ./start.sh status       # show running proxy + log dir
#   ./start.sh logs         # print recent proxy stderr (background mode)
#
# Env overrides:
#   AI_OBS_LAB_CONFIG=path/to/proxy.yaml
#   AI_OBS_LAB_LOG_DIR=~/.ai-obs-lab/logs

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="${HERE}/src${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONPATH
PY="${PYTHON:-python3}"

STATE_DIR="${HOME}/.ai-obs-lab"
mkdir -p "${STATE_DIR}"
PID_FILE="${STATE_DIR}/proxy.pid"
LOG_FILE="${STATE_DIR}/proxy.stderr.log"

# 注意：set -u 下，空数组用 "${arr[@]}" 展开会触发 unbound variable，
# 因此后续展开必须用 "${arr[@]:-}" 这种带默认值的写法，或者先填一个再清空。
cfg_arg=()
if [[ -n "${AI_OBS_LAB_CONFIG:-}" ]]; then
  cfg_arg=(--config "${AI_OBS_LAB_CONFIG}")
fi
logdir_arg=()
if [[ -n "${AI_OBS_LAB_LOG_DIR:-}" ]]; then
  logdir_arg=(--log-dir "${AI_OBS_LAB_LOG_DIR}")
fi

cmd="${1:-default}"

case "${cmd}" in
  default)
    if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
      echo "[ai-obs-lab] proxy already running (pid $(cat "${PID_FILE}"))"
    else
      echo "[ai-obs-lab] starting proxy in background; stderr -> ${LOG_FILE}"
      nohup "${PY}" -m ai_obs_lab.cli proxy "${cfg_arg[@]:-}" "${logdir_arg[@]:-}" \
        >>"${LOG_FILE}" 2>&1 &
      echo $! > "${PID_FILE}"
      sleep 0.3
    fi
    echo "[ai-obs-lab] tailing (Ctrl-C to stop tail; proxy keeps running)"
    exec "${PY}" -m ai_obs_lab.cli tail "${logdir_arg[@]}"
    ;;
  proxy)
    exec "${PY}" -m ai_obs_lab.cli proxy "${cfg_arg[@]:-}" "${logdir_arg[@]:-}"
    ;;
  tail)
    exec "${PY}" -m ai_obs_lab.cli tail "${logdir_arg[@]:-}"
    ;;
  report)
    shift || true
    "${PY}" -m ai_obs_lab.cli report --date today --open "${logdir_arg[@]:-}" "$@"
    ;;
  stop)
    if [[ -f "${PID_FILE}" ]]; then
      pid="$(cat "${PID_FILE}")"
      if kill -0 "${pid}" 2>/dev/null; then
        kill "${pid}"
        echo "[ai-obs-lab] stopped pid ${pid}"
      else
        echo "[ai-obs-lab] stale pid file (${pid} not running)"
      fi
      rm -f "${PID_FILE}"
    else
      echo "[ai-obs-lab] no pid file at ${PID_FILE}"
    fi
    ;;
  status)
    if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
      echo "[ai-obs-lab] proxy running, pid=$(cat "${PID_FILE}")"
    else
      echo "[ai-obs-lab] proxy NOT running"
    fi
    echo "  log_dir: ${AI_OBS_LAB_LOG_DIR:-~/.ai-obs-lab/logs}"
    echo "  stderr:  ${LOG_FILE}"
    ;;
  logs)
    tail -n 100 "${LOG_FILE}" 2>/dev/null || echo "[ai-obs-lab] no logs yet"
    ;;
  *)
    echo "usage: $0 [default|proxy|tail|report|stop|status|logs]" >&2
    exit 2
    ;;
esac
