"""providers 包：统一供应商接口、流式事件与适配器工厂。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

from majiecode.config import ProviderConfig
from majiecode.session import Message


@dataclass
class StreamEvent:
    """供应商统一输出的流式事件。

    kind: thinking / text / error / end
    """

    kind: str
    content: str = ""


class Provider(ABC):
    """供应商抽象接口。新增后端只需实现本类。"""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def stream(self, messages: list[Message]) -> Iterator[StreamEvent]:
        """给定对话历史，返回流式事件迭代器。"""
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
