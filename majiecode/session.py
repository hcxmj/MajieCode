"""会话层：维护本次对话的消息历史。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Message:
    """一条对话消息。"""

    role: str  # system / user / assistant
    content: str


class Session:
    """本次会话的历史管理，仅内存保留。"""

    def __init__(self, system_prompt: str) -> None:
        self._system_prompt = system_prompt
        self._messages: list[Message] = [Message("system", system_prompt)]

    def add_user(self, content: str) -> None:
        self._messages.append(Message("user", content))

    def add_assistant(self, content: str) -> None:
        self._messages.append(Message("assistant", content))

    def clear(self) -> None:
        """清空历史，仅保留系统提示。"""
        self._messages = [Message("system", self._system_prompt)]

    def messages(self) -> list[Message]:
        """返回完整消息列表（含 system）。"""
        return list(self._messages)
