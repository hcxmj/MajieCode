"""界面层：prompt_toolkit 输入 + Rich 流式渲染 + 控制命令。"""
from __future__ import annotations

from collections.abc import Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from majiecode.providers import StreamEvent

# 控制命令集合
COMMANDS = {"/exit", "/clear", "/help"}

_HELP_TEXT = """[bold]可用命令[/bold]
  /help   显示本帮助
  /clear  清空当前会话历史
  /exit   退出 MajieCode
其余输入将作为提问发送给模型。"""


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

    def render_stream(self, events: Iterable[StreamEvent]) -> str:
        """逐事件渲染流式输出，返回累积的正式回复文本。"""
        text_parts: list[str] = []
        in_thinking = False
        started_text = False

        for ev in events:
            if ev.kind == "thinking":
                if not in_thinking:
                    self._console.print("[dim italic]思考中……[/dim italic]")
                    in_thinking = True
                self._console.print(f"[dim italic]{ev.content}[/dim italic]", end="")
            elif ev.kind == "text":
                if in_thinking:
                    self._console.print()  # 思考与正文之间换行
                    in_thinking = False
                started_text = True
                text_parts.append(ev.content)
                self._console.print(ev.content, end="")
            elif ev.kind == "error":
                if in_thinking or started_text:
                    self._console.print()
                self.show_error(ev.content)
            elif ev.kind == "end":
                if in_thinking or started_text:
                    self._console.print()  # 收尾换行

        return "".join(text_parts)
