"""Anthropic 原生协议适配器，支持 extended thinking。"""
from __future__ import annotations

from collections.abc import Iterator

from majiecode.config import ProviderConfig
from majiecode.providers import Provider, StreamEvent
from majiecode.session import Message

# 思考预算与回复上限；开启 thinking 时 max_tokens 必须大于 budget_tokens
_THINKING_BUDGET = 1600
_MAX_TOKENS = 4096


class AnthropicProvider(Provider):
    """基于 Anthropic SDK 的流式对话适配器。"""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        import anthropic

        self._client = anthropic.Anthropic(
            api_key=config.api_key, base_url=config.base_url
        )

    def stream(self, messages: list[Message]) -> Iterator[StreamEvent]:
        # Anthropic 的 system 提示是独立参数，需从消息列表中剥离
        system_prompt = ""
        convo = []
        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            else:
                convo.append({"role": m.role, "content": m.content})

        kwargs = {
            "model": self.config.model,
            "max_tokens": _MAX_TOKENS,
            "messages": convo,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if self.config.thinking:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": _THINKING_BUDGET,
            }

        try:
            with self._client.messages.stream(**kwargs) as stream:
                for event in stream:
                    if event.type == "thinking":
                        yield StreamEvent("thinking", event.thinking)
                    elif event.type == "text":
                        yield StreamEvent("text", event.text)
        except Exception as e:  # noqa: BLE001
            yield StreamEvent("error", f"{type(e).__name__}: {e}")
        finally:
            yield StreamEvent("end")
