"""检索工具：按 glob 找文件、按正则搜文件内容（纯标准库）。"""
from __future__ import annotations

import fnmatch
import glob
import os
import re

from majiecode.tools.base import ExecContext, Tool, ToolParam, ToolResult
from majiecode.tools.safety import PathEscapeError, resolve_in_workdir

_MAX_FILE_BYTES = 2 * 1024 * 1024  # 跳过超过 2MB 的文件
_MAX_HITS = 500  # grep 命中上限


class GlobTool(Tool):
    """按 glob 模式在工作目录内查找文件。"""

    name = "glob_files"
    description = "按 glob 模式在工作目录内查找文件，返回相对路径列表。支持 ** 递归。"
    parameters = [
        ToolParam("pattern", "string", "glob 模式，如 **/*.py 或 src/*.txt"),
    ]

    def __init__(self, ctx: ExecContext) -> None:
        self.ctx = ctx

    def run(self, args: dict) -> ToolResult:
        pattern = args.get("pattern")
        if not pattern:
            return ToolResult.fail("缺少参数 pattern")
        try:
            full = os.path.join(self.ctx.workdir, pattern)
            matches = glob.glob(full, recursive=True)
            rels = sorted(
                os.path.relpath(m, self.ctx.workdir)
                for m in matches
                if os.path.isfile(m)
            )
            if not rels:
                return ToolResult.success(f"无匹配：{pattern}")
            return ToolResult.success("\n".join(rels))
        except Exception as e:  # noqa: BLE001
            return ToolResult.fail(f"{type(e).__name__}: {e}")


class GrepTool(Tool):
    """按正则在工作目录内检索文件内容。"""

    name = "grep"
    description = (
        "按正则表达式搜索文件内容，返回 路径:行号:行文本。"
        "可选 path 限定子目录/文件，可选 glob 过滤文件名。"
    )
    parameters = [
        ToolParam("pattern", "string", "正则表达式"),
        ToolParam("path", "string", "搜索的子目录或文件（可选，默认工作目录）", required=False),
        ToolParam("glob", "string", "文件名过滤，如 *.py（可选）", required=False),
    ]

    def __init__(self, ctx: ExecContext) -> None:
        self.ctx = ctx

    def run(self, args: dict) -> ToolResult:
        pattern = args.get("pattern")
        if not pattern:
            return ToolResult.fail("缺少参数 pattern")
        name_glob = args.get("glob")
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult.fail(f"正则表达式非法：{e}")
        try:
            root = resolve_in_workdir(self.ctx.workdir, args.get("path") or ".")
        except PathEscapeError as e:
            return ToolResult.fail(str(e))

        hits: list[str] = []
        try:
            targets = [root] if os.path.isfile(root) else self._walk_files(root)
            for fpath in targets:
                if name_glob and not fnmatch.fnmatch(
                    os.path.basename(fpath), name_glob
                ):
                    continue
                for hit in self._search_file(fpath, regex):
                    hits.append(hit)
                    if len(hits) >= _MAX_HITS:
                        hits.append(f"…（命中超过 {_MAX_HITS} 处，已截断）")
                        return ToolResult.success("\n".join(hits))
            if not hits:
                return ToolResult.success(f"无命中：{pattern}")
            return ToolResult.success("\n".join(hits))
        except Exception as e:  # noqa: BLE001
            return ToolResult.fail(f"{type(e).__name__}: {e}")

    def _walk_files(self, root: str):
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                yield os.path.join(dirpath, name)

    def _search_file(self, fpath: str, regex: "re.Pattern"):
        try:
            if os.path.getsize(fpath) > _MAX_FILE_BYTES:
                return
            with open(fpath, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if regex.search(line):
                        rel = os.path.relpath(fpath, self.ctx.workdir)
                        yield f"{rel}:{lineno}:{line.rstrip()}"
        except (UnicodeDecodeError, OSError):
            return  # 跳过二进制或不可读文件
