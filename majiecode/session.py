"""会话层：维护本次对话的消息历史。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Message:
    """一条对话消息。

    普通消息只用 role/content；工具交互时：
    - assistant 发起调用：tool_calls 承载本轮工具调用列表；
    - role="tool" 结果：tool_call_id 指明对应调用，name 为工具名。
    """

    role: str  # system / user / assistant / tool
    content: str
    tool_calls: list | None = None
    tool_call_id: str | None = None
    name: str | None = None


class Session:
    """本次会话的历史管理，仅内存保留。"""

    def __init__(self, system_prompt: str) -> None:
        self._system_prompt = system_prompt
        self._messages: list[Message] = [Message("system", system_prompt)]

    def add_user(self, content: str) -> None:
        self._messages.append(Message("user", content))

    def add_assistant(self, content: str, tool_calls: list | None = None) -> None:
        self._messages.append(Message("assistant", content, tool_calls=tool_calls))

    def add_tool_result(self, tool_call_id: str, name: str, output: str) -> None:
        """追加一条工具执行结果消息（role="tool"）。"""
        self._messages.append(
            Message("tool", output, tool_call_id=tool_call_id, name=name)
        )

    def clear(self) -> None:
        """清空历史，仅保留系统提示。"""
        self._messages = [Message("system", self._system_prompt)]

    def messages(self) -> list[Message]:
        """返回完整消息列表（含 system）。"""
        return list(self._messages)
