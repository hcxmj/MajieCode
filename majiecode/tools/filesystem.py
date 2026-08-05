"""文件工具：读文件、写文件、改文件（唯一匹配替换）。"""
from __future__ import annotations

import os

from majiecode.tools.base import ExecContext, Tool, ToolParam, ToolResult
from majiecode.tools.safety import PathEscapeError, resolve_in_workdir


class ReadFileTool(Tool):
    """读取工作目录内的文本文件内容。"""

    name = "read_file"
    description = "读取指定文本文件的完整内容。路径限工作目录内。"
    parameters = [
        ToolParam("path", "string", "要读取的文件路径（相对工作目录或绝对路径）"),
    ]

    def __init__(self, ctx: ExecContext) -> None:
        self.ctx = ctx

    def run(self, args: dict) -> ToolResult:
        path = args.get("path")
        if not path:
            return ToolResult.fail("缺少参数 path")
        try:
            real = resolve_in_workdir(self.ctx.workdir, path)
            with open(real, "r", encoding="utf-8") as f:
                return ToolResult.success(f.read())
        except PathEscapeError as e:
            return ToolResult.fail(str(e))
        except FileNotFoundError:
            return ToolResult.fail(f"文件不存在：{path}")
        except IsADirectoryError:
            return ToolResult.fail(f"这是一个目录而非文件：{path}")
        except UnicodeDecodeError:
            return ToolResult.fail(f"文件不是 UTF-8 文本，无法读取：{path}")
        except Exception as e:  # noqa: BLE001
            return ToolResult.fail(f"{type(e).__name__}: {e}")


class WriteFileTool(Tool):
    """创建或整体覆盖写入文件，自动创建缺失的父目录。"""

    name = "write_file"
    description = "把内容写入文件（创建或整体覆盖）。父目录会自动创建。路径限工作目录内。"
    parameters = [
        ToolParam("path", "string", "要写入的文件路径（相对工作目录或绝对路径）"),
        ToolParam("content", "string", "要写入的完整文本内容"),
    ]

    def __init__(self, ctx: ExecContext) -> None:
        self.ctx = ctx

    def run(self, args: dict) -> ToolResult:
        path = args.get("path")
        if not path:
            return ToolResult.fail("缺少参数 path")
        content = args.get("content", "")
        try:
            real = resolve_in_workdir(self.ctx.workdir, path)
            parent = os.path.dirname(real)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(real, "w", encoding="utf-8") as f:
                f.write(content)
            rel = os.path.relpath(real, self.ctx.workdir)
            return ToolResult.success(f"已写入 {len(content)} 字符到 {rel}")
        except PathEscapeError as e:
            return ToolResult.fail(str(e))
        except Exception as e:  # noqa: BLE001
            return ToolResult.fail(f"{type(e).__name__}: {e}")


class EditFileTool(Tool):
    """原文唯一匹配替换：old_string 必须恰好出现一次。"""

    name = "edit_file"
    description = (
        "在文件中把 old_string 替换成 new_string。"
        "old_string 必须在文件中恰好出现一次，否则报错以便重试。"
    )
    parameters = [
        ToolParam("path", "string", "要修改的文件路径（相对工作目录或绝对路径）"),
        ToolParam("old_string", "string", "被替换的原文片段，需在文件中唯一"),
        ToolParam("new_string", "string", "替换后的新片段"),
    ]

    def __init__(self, ctx: ExecContext) -> None:
        self.ctx = ctx

    def run(self, args: dict) -> ToolResult:
        path = args.get("path")
        old = args.get("old_string")
        new = args.get("new_string", "")
        if not path:
            return ToolResult.fail("缺少参数 path")
        if old is None:
            return ToolResult.fail("缺少参数 old_string")
        try:
            real = resolve_in_workdir(self.ctx.workdir, path)
            with open(real, "r", encoding="utf-8") as f:
                text = f.read()
            count = text.count(old)
            if count == 0:
                return ToolResult.fail(f"未匹配到 old_string，未修改文件：{path}")
            if count > 1:
                return ToolResult.fail(
                    f"old_string 匹配到 {count} 处，需提供更精确的上下文以保证唯一，未修改文件"
                )
            with open(real, "w", encoding="utf-8") as f:
                f.write(text.replace(old, new, 1))
            rel = os.path.relpath(real, self.ctx.workdir)
            return ToolResult.success(f"已替换 {rel} 中的 1 处")
        except PathEscapeError as e:
            return ToolResult.fail(str(e))
        except FileNotFoundError:
            return ToolResult.fail(f"文件不存在：{path}")
        except UnicodeDecodeError:
            return ToolResult.fail(f"文件不是 UTF-8 文本，无法编辑：{path}")
        except Exception as e:  # noqa: BLE001
            return ToolResult.fail(f"{type(e).__name__}: {e}")
