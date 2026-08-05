"""工具基础设施：参数 Schema、结构化结果、工具抽象、执行上下文。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolParam:
    """工具的一个参数定义，用于生成 JSON Schema。"""

    name: str
    type: str  # JSON Schema 类型：string / integer / number / boolean / array 等
    description: str
    required: bool = True


@dataclass
class ToolResult:
    """工具执行的结构化结果，区分成功与失败。"""

    ok: bool
    output: str = ""
    error: str = ""

    @classmethod
    def success(cls, output: str) -> "ToolResult":
        return cls(ok=True, output=output)

    @classmethod
    def fail(cls, error: str) -> "ToolResult":
        return cls(ok=False, error=error)

    def to_model_text(self) -> str:
        """压成回灌给模型的纯文本：成功给 output，失败给「错误：…」。"""
        if self.ok:
            return self.output
        return f"错误：{self.error}"


@dataclass
class ExecContext:
    """工具执行上下文：所有工具据此做路径解析与越界校验。"""

    workdir: str


class Tool(ABC):
    """工具抽象基类。新增工具只需继承并实现 run，再登记到注册中心。"""

    name: str = ""
    description: str = ""
    parameters: list[ToolParam] = []

    @abstractmethod
    def run(self, args: dict) -> ToolResult:
        """接收已解析的参数字典，执行并返回结构化结果。"""
        raise NotImplementedError

    def input_schema(self) -> dict:
        """由 parameters 生成 JSON Schema（object + properties + required）。"""
        properties: dict[str, dict] = {}
        required: list[str] = []
        for p in self.parameters:
            properties[p.name] = {"type": p.type, "description": p.description}
            if p.required:
                required.append(p.name)
        return {"type": "object", "properties": properties, "required": required}
