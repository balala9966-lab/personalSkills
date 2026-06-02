"""stdio MCP 通用拦截 wrapper。

把任意一个用 stdio 通信的 MCP server 包在中间，让你能看到 MCP client（如
Claude Code / cfuse）和 server 之间真实流过的 JSON-RPC 帧 —— tools/list 暴露
了哪些工具菜单、每次 tools/call 传了什么 params、server 返回了什么 result，
全部 tee 到 store 落盘，再由实时看板展示。

用法：
    python -m ai_obs_lab.cli mcp -- <真实 mcp server 命令...>
例如：
    python -m ai_obs_lab.cli mcp -- npx -y @modelcontextprotocol/server-filesystem /tmp

原理：
    上游 client  --stdin-->  [本 wrapper]  --stdin-->  真实 MCP server
    上游 client  <-stdout--  [本 wrapper]  <-stdout--  真实 MCP server
两个方向各起一个转发线程，逐帧透明转发的同时 tee 一份到 store。
stdio MCP 使用「按行分隔的 JSON」（newline-delimited JSON-RPC）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from typing import IO

from ..core.store import JSONLStore


def _classify(payload: dict) -> tuple[str | None, str]:
    """从一帧 JSON-RPC 里提取 (method, kind)，仅用于看板分类展示。

    kind 取值：request / response / error / notification / unknown。
    不修改 payload 本身（保持原文）。
    """
    if not isinstance(payload, dict):
        return None, "unknown"
    method = payload.get("method")
    has_id = "id" in payload
    if method is not None and has_id:
        return method, "request"
    if method is not None and not has_id:
        return method, "notification"
    if "error" in payload:
        return None, "error"
    if "result" in payload:
        return None, "response"
    return method, "unknown"


def _pump(
    src: IO[bytes],
    dst: IO[bytes],
    *,
    direction: str,
    store: JSONLStore,
    session_id: str,
) -> None:
    """把 src 的每一行透明转发到 dst，同时 tee 一份 JSON-RPC 帧到 store。

    透明转发优先：即使某一行不是合法 JSON（如 server 打到 stdout 的日志），
    也照常转发，只是不落盘为帧，避免破坏协议。
    """
    try:
        for raw in iter(src.readline, b""):
            # 先转发，确保协议不被阻塞或破坏。
            try:
                dst.write(raw)
                dst.flush()
            except (BrokenPipeError, ValueError):
                break
            line = raw.strip()
            if not line:
                continue
            try:
                payload = json.loads(line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue  # 非 JSON 行（日志等）只转发不落盘
            method, kind = _classify(payload)
            try:
                store.append_mcp_frame(
                    session_id,
                    ts=time.time(),
                    direction=direction,
                    payload=payload,
                    method=method,
                    kind=kind,
                )
            except Exception:
                # 落盘失败绝不能影响转发；观测是旁路。
                pass
    finally:
        try:
            dst.close()
        except Exception:
            pass


def run_mcp_wrapper(
    command: list[str],
    *,
    store: JSONLStore | None = None,
    label: str | None = None,
) -> int:
    """启动真实 MCP server 并双向转发，全程 tee JSON-RPC 帧。

    command 来自 argparse.REMAINDER，可能以 "--" 打头，这里剥掉。
    返回子进程退出码。
    """
    store = store or JSONLStore()
    cmd = list(command)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        sys.stderr.write("[mcp] 缺少真实 MCP server 命令\n")
        return 2

    session_id = time.strftime("%H%M%S-") + uuid.uuid4().hex[:6]
    command_str = " ".join(cmd)
    ts_start = time.time()
    store.write_mcp_meta(session_id, command_str, ts_start, label=label)
    sys.stderr.write(
        f"[mcp] 包裹 stdio MCP：{command_str}\n"
        f"[mcp] 会话 {session_id} 的 JSON-RPC 帧落盘到 {store.base_dir}/<date>/mcp/\n"
    )

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,  # server 的 stderr 直接透传到终端，便于调试
        bufsize=0,
        env=os.environ.copy(),
    )

    # client(stdin) -> server(proc.stdin)
    to_server = threading.Thread(
        target=_pump,
        args=(sys.stdin.buffer, proc.stdin),
        kwargs=dict(direction="client->server", store=store, session_id=session_id),
        daemon=True,
    )
    # server(proc.stdout) -> client(stdout)
    to_client = threading.Thread(
        target=_pump,
        args=(proc.stdout, sys.stdout.buffer),
        kwargs=dict(direction="server->client", store=store, session_id=session_id),
        daemon=True,
    )
    to_server.start()
    to_client.start()

    try:
        rc = proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        rc = proc.wait()
    # 等转发线程把剩余输出冲刷完。
    to_client.join(timeout=2)
    return rc
