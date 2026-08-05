"""工具注册中心：登记、按名查找、导出两族 API 工具声明。"""
from __future__ import annotations

from majiecode.tools.base import ExecContext, Tool
from majiecode.tools.filesystem import EditFileTool, ReadFileTool, WriteFileTool
from majiecode.tools.search import GlobTool, GrepTool
from majiecode.tools.shell import RunCommandTool


class Registry:
    """集中登记工具，支持按名查找与两族声明导出。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"工具重名：{tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def to_openai_schema(self) -> list[dict]:
        """导出 OpenAI Chat Completions 的 tools 声明。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema(),
                },
            }
            for t in self._tools.values()
        ]

    def to_anthropic_schema(self) -> list[dict]:
        """导出 Anthropic Messages 的 tools 声明。"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema(),
            }
            for t in self._tools.values()
        ]


def build_default_registry(ctx: ExecContext) -> Registry:
    """构造并登记六个核心工具。"""
    registry = Registry()
    registry.register(ReadFileTool(ctx))
    registry.register(WriteFileTool(ctx))
    registry.register(EditFileTool(ctx))
    registry.register(RunCommandTool(ctx))
    registry.register(GlobTool(ctx))
    registry.register(GrepTool(ctx))
    return registry
