"""Anthropic 原生协议适配器，支持 extended thinking 与工具调用。"""
from __future__ import annotations

import json
from collections.abc import Iterator

from majiecode.config import ProviderConfig
from majiecode.providers import Provider, StreamEvent, ToolCall
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

    def _to_payload(self, messages: list[Message]) -> tuple[str, list[dict]]:
        """把富消息转成 (system, convo)；system 为独立参数。

        assistant 的工具调用转成 tool_use block；role="tool" 结果合并进
        紧邻的 user 消息的 tool_result block。
        """
        system_prompt = ""
        convo: list[dict] = []
        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            elif m.role == "assistant" and m.tool_calls:
                content: list[dict] = []
                if m.content:
                    content.append({"type": "text", "text": m.content})
                for c in m.tool_calls:
                    content.append(
                        {
                            "type": "tool_use",
                            "id": c.id,
                            "name": c.name,
                            "input": c.arguments,
                        }
                    )
                convo.append({"role": "assistant", "content": content})
            elif m.role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": m.tool_call_id,
                    "content": m.content,
                }
                # 连续的工具结果合并进同一条 user 消息
                if convo and convo[-1]["role"] == "user" and isinstance(
                    convo[-1]["content"], list
                ):
                    convo[-1]["content"].append(block)
                else:
                    convo.append({"role": "user", "content": [block]})
            else:
                convo.append({"role": m.role, "content": m.content})
        return system_prompt, convo

    def stream(
        self, messages: list[Message], tools: list[dict] | None = None
    ) -> Iterator[StreamEvent]:
        system_prompt, convo = self._to_payload(messages)

        kwargs = {
            "model": self.config.model,
            "max_tokens": _MAX_TOKENS,
            "messages": convo,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = tools
        if self.config.thinking:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": _THINKING_BUDGET,
            }

        # 当前正在累积的 tool_use 块：{"id","name","buf"}
        cur_tool: dict | None = None
        try:
            with self._client.messages.stream(**kwargs) as stream:
                for event in stream:
                    etype = event.type
                    if etype == "content_block_start":
                        block = event.content_block
                        if getattr(block, "type", None) == "tool_use":
                            cur_tool = {"id": block.id, "name": block.name, "buf": ""}
                    elif etype == "content_block_delta":
                        delta = event.delta
                        dtype = getattr(delta, "type", None)
                        if dtype == "thinking_delta":
                            yield StreamEvent("thinking", delta.thinking)
                        elif dtype == "text_delta":
                            yield StreamEvent("text", delta.text)
                        elif dtype == "input_json_delta" and cur_tool is not None:
                            cur_tool["buf"] += delta.partial_json
                    elif etype == "content_block_stop":
                        if cur_tool is not None:
                            try:
                                arguments = json.loads(cur_tool["buf"] or "{}")
                            except json.JSONDecodeError:
                                arguments = {}
                            yield StreamEvent(
                                "tool_call",
                                tool_call=ToolCall(
                                    cur_tool["id"], cur_tool["name"], arguments
                                ),
                            )
                            cur_tool = None
        except Exception as e:  # noqa: BLE001
            yield StreamEvent("error", f"{type(e).__name__}: {e}")
        finally:
            yield StreamEvent("end")
