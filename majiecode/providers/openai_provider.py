"""OpenAI 兼容族适配器：覆盖 DeepSeek/Qwen/豆包/MiniMax/GLM/OpenAI。"""
from __future__ import annotations

import json
from collections.abc import Iterator

from majiecode.config import ProviderConfig
from majiecode.providers import Provider, StreamEvent, ToolCall
from majiecode.session import Message


class OpenAIProvider(Provider):
    """基于 OpenAI SDK 的流式对话适配器。"""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        from openai import OpenAI

        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def _to_payload(self, messages: list[Message]) -> list[dict]:
        """把富消息历史转成 OpenAI Chat Completions 格式。"""
        payload: list[dict] = []
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                payload.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": [
                            {
                                "id": c.id,
                                "type": "function",
                                "function": {
                                    "name": c.name,
                                    "arguments": json.dumps(
                                        c.arguments, ensure_ascii=False
                                    ),
                                },
                            }
                            for c in m.tool_calls
                        ],
                    }
                )
            elif m.role == "tool":
                payload.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.tool_call_id,
                        "content": m.content,
                    }
                )
            else:
                payload.append({"role": m.role, "content": m.content})
        return payload

    def stream(
        self, messages: list[Message], tools: list[dict] | None = None
    ) -> Iterator[StreamEvent]:
        payload = self._to_payload(messages)
        want_thinking = self.config.thinking
        # index -> {"id", "name", "args"} 累积分片的工具调用
        acc: dict[int, dict] = {}
        try:
            kwargs = {
                "model": self.config.model,
                "messages": payload,
                "stream": True,
            }
            if tools:
                kwargs["tools"] = tools
            stream = self._client.chat.completions.create(**kwargs)
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
                # 工具调用分片：按 index 拼接 arguments 碎片
                for tc in getattr(delta, "tool_calls", None) or []:
                    slot = acc.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["args"] += tc.function.arguments
            # 流结束：产出拼接完成的完整工具调用
            for _idx in sorted(acc):
                slot = acc[_idx]
                try:
                    arguments = json.loads(slot["args"] or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                yield StreamEvent(
                    "tool_call",
                    tool_call=ToolCall(slot["id"], slot["name"], arguments),
                )
        except Exception as e:  # noqa: BLE001
            yield StreamEvent("error", f"{type(e).__name__}: {e}")
        finally:
            yield StreamEvent("end")
