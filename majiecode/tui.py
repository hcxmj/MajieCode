"""界面层：prompt_toolkit 输入 + Rich 流式渲染 + 控制命令。"""
from __future__ import annotations

import json
from collections.abc import Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from majiecode.providers import StreamEvent, ToolCall
from majiecode.tools.base import ToolResult

# 控制命令集合
COMMANDS = {"/exit", "/clear", "/help"}

_HELP_TEXT = """[bold]可用命令[/bold]
  /help   显示本帮助
  /clear  清空当前会话历史
  /exit   退出 MajieCode
其余输入将作为提问发送给模型。"""

_SUMMARY_LIMIT = 500  # 结果摘要截断长度


def _truncate(text: str, limit: int = _SUMMARY_LIMIT) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "…"


class Tui:
    """终端交互界面。"""

    def __init__(self) -> None:
        self._console = Console()
        self._session = PromptSession(history=InMemoryHistory())

    def prompt_user(self) -> str:
        """读取一行用户输入（支持行编辑与上下历史）。"""
        return self._session.prompt("❯ ").strip()

    def show_info(self, text: str) -> None:
        self._console.print(f"[dim]{text}[/dim]")

    def show_error(self, text: str) -> None:
        self._console.print(f"[bold red]错误：[/bold red]{text}")

    def show_help(self) -> None:
        self._console.print(_HELP_TEXT)

    def show_tool_call(self, call: ToolCall) -> None:
        """展示模型发起的一次工具调用。"""
        args = _truncate(json.dumps(call.arguments, ensure_ascii=False))
        self._console.print(f"[cyan]⚙ 调用 {call.name}[/cyan] [dim]{args}[/dim]")

    def show_tool_result(self, name: str, result: ToolResult) -> None:
        """展示工具执行结果摘要。"""
        if result.ok:
            self._console.print(
                f"[green]✓ {name} 完成[/green] [dim]{_truncate(result.output)}[/dim]"
            )
        else:
            self._console.print(f"[bold red]✗ {name} 失败：[/bold red]{result.error}")

    def render_stream(
        self, events: Iterable[StreamEvent]
    ) -> tuple[str, list[ToolCall]]:
        """逐事件渲染流式输出，返回（正式回复文本, 工具调用列表）。"""
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        in_thinking = False
        started_text = False

        for ev in events:
            if ev.kind == "thinking":
                if not in_thinking:
                    self._console.print("[dim italic]思考中……[/dim italic]")
                    in_thinking = True
                self._console.print(
                    f"[dim italic]{ev.content}[/dim italic]", end=""
                )
            elif ev.kind == "text":
                if in_thinking:
                    self._console.print()  # 思考与正文之间换行
                    in_thinking = False
                started_text = True
                text_parts.append(ev.content)
                self._console.print(ev.content, end="")
            elif ev.kind == "tool_call":
                if in_thinking or started_text:
                    self._console.print()
                    in_thinking = False
                    started_text = False
                if ev.tool_call is not None:
                    tool_calls.append(ev.tool_call)
            elif ev.kind == "error":
                if in_thinking or started_text:
                    self._console.print()
                self.show_error(ev.content)
            elif ev.kind == "end":
                if in_thinking or started_text:
                    self._console.print()  # 收尾换行

        return "".join(text_parts), tool_calls
