"""OpenAI 兼容族适配器：覆盖 DeepSeek/Qwen/豆包/MiniMax/GLM/OpenAI。"""
from __future__ import annotations

from collections.abc import Iterator

from majiecode.config import ProviderConfig
from majiecode.providers import Provider, StreamEvent
from majiecode.session import Message


class OpenAIProvider(Provider):
    """基于 OpenAI SDK 的流式对话适配器。"""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        from openai import OpenAI

        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def stream(self, messages: list[Message]) -> Iterator[StreamEvent]:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        want_thinking = self.config.thinking
        try:
            stream = self._client.chat.completions.create(
                model=self.config.model,
                messages=payload,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                # 思考内容：兼容 DeepSeek/GLM/Qwen 的 reasoning_content 字段
                if want_thinking:
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning:
                        yield StreamEvent("thinking", reasoning)
                if delta.content:
                    yield StreamEvent("text", delta.content)
        except Exception as e:  # noqa: BLE001
            yield StreamEvent("error", f"{type(e).__name__}: {e}")
        finally:
            yield StreamEvent("end")
