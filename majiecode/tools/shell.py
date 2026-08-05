"""命令执行工具：在工作目录内执行 shell 命令，带超时与输出捕获。"""
from __future__ import annotations

import subprocess

from majiecode.tools.base import ExecContext, Tool, ToolParam, ToolResult

_DEFAULT_TIMEOUT = 30  # 秒


class RunCommandTool(Tool):
    """在工作目录内执行 shell 命令，捕获 stdout/stderr/退出码。"""

    name = "run_command"
    description = (
        "在工作目录下执行一条 shell 命令，返回退出码、标准输出与标准错误。"
        f"默认超时 {_DEFAULT_TIMEOUT} 秒。"
    )
    parameters = [
        ToolParam("command", "string", "要执行的 shell 命令"),
        ToolParam("timeout", "integer", "超时秒数（可选，默认 30）", required=False),
    ]

    def __init__(self, ctx: ExecContext) -> None:
        self.ctx = ctx

    def run(self, args: dict) -> ToolResult:
        command = args.get("command")
        if not command:
            return ToolResult.fail("缺少参数 command")
        timeout = args.get("timeout") or _DEFAULT_TIMEOUT
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.ctx.workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            parts = [f"退出码: {proc.returncode}"]
            if proc.stdout:
                parts.append(f"[stdout]\n{proc.stdout}")
            if proc.stderr:
                parts.append(f"[stderr]\n{proc.stderr}")
            return ToolResult.success("\n".join(parts))
        except subprocess.TimeoutExpired:
            return ToolResult.fail(f"命令超时（>{timeout}s），已中止")
        except Exception as e:  # noqa: BLE001
            return ToolResult.fail(f"{type(e).__name__}: {e}")
