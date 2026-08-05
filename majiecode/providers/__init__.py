"""providers 包：统一供应商接口、流式事件、工具调用与适配器工厂。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field

from majiecode.config import ProviderConfig
from majiecode.session import Message


@dataclass
class ToolCall:
    """一次完整的工具调用（JSON 参数碎片已拼接解析）。"""

    id: str
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass
class StreamEvent:
    """供应商统一输出的流式事件。

    kind: thinking / text / tool_call / error / end
    tool_call 仅在 kind == "tool_call" 时有值。
    """

    kind: str
    content: str = ""
    tool_call: "ToolCall | None" = None


class Provider(ABC):
    """供应商抽象接口。新增后端只需实现本类。"""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def stream(
        self, messages: list[Message], tools: list[dict] | None = None
    ) -> Iterator[StreamEvent]:
        """给定对话历史与可选工具声明，返回流式事件迭代器。"""
        raise NotImplementedError


def create_provider(cfg: ProviderConfig) -> Provider:
    """按 protocol 分派创建供应商实例。"""
    if cfg.protocol == "openai":
        from majiecode.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(cfg)
    if cfg.protocol == "anthropic":
        from majiecode.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(cfg)
    raise ValueError(f"未知协议：{cfg.protocol}")
