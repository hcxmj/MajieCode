"""路径安全：把路径解析为工作目录内的绝对路径，越界则拒绝。"""
from __future__ import annotations

import os


class PathEscapeError(Exception):
    """路径越出工作目录时抛出。"""


def resolve_in_workdir(workdir: str, path: str) -> str:
    """把 path（相对则相对 workdir）规范化为绝对路径并校验位于 workdir 内。

    通过 realpath 消解符号链接与 `..`，再用 commonpath 比对，
    防止 `../` 越界、符号链接逃逸与绝对路径逃逸。越界抛 PathEscapeError。
    """
    base = os.path.realpath(workdir)
    target = path if os.path.isabs(path) else os.path.join(base, path)
    real_target = os.path.realpath(target)

    if real_target != base and os.path.commonpath([base, real_target]) != base:
        raise PathEscapeError(f"路径越出工作目录，已拒绝：{path}")
    return real_target
