"""入口层：参数解析、装配各层、驱动主循环。"""
from __future__ import annotations

import argparse
import os
import sys

from majiecode.config import ConfigError, load_config
from majiecode.providers import create_provider
from majiecode.session import Session
from majiecode.tui import Tui

_SYSTEM_PROMPT = (
    "你是 MajieCode，一个运行在终端里的 AI 编程助手。用简洁的中文回答。"
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="majiecode", description="终端 AI 编程助手（交互式对话）"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="YAML 配置文件路径（默认取 MAJIECODE_CONFIG 环境变量，否则当前目录 config.yaml）",
    )
    parser.add_argument(
        "--provider", default=None, help="临时指定使用的供应商 name（覆盖 default）"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    tui = Tui()

    # 配置路径优先级：--config > MAJIECODE_CONFIG 环境变量 > 当前目录 config.yaml
    config_path = args.config or os.environ.get("MAJIECODE_CONFIG") or "config.yaml"

    # 装配：加载配置 → 选供应商 → 建 provider 与 session
    try:
        app_cfg = load_config(config_path)
        cfg = app_cfg.select(args.provider)
        provider = create_provider(cfg)
    except ConfigError as e:
        tui.show_error(str(e))
        return 1
    except Exception as e:  # noqa: BLE001
        tui.show_error(f"初始化失败：{type(e).__name__}: {e}")
        return 1

    session = Session(_SYSTEM_PROMPT)
    tui.show_info(f"MajieCode · {cfg.name} · {cfg.model}"
                  + ("（思考已开启）" if cfg.thinking else ""))
    tui.show_info("输入 /help 查看命令，/exit 退出。")

    while True:
        try:
            text = tui.prompt_user()
        except (EOFError, KeyboardInterrupt):
            tui.show_info("\n再见。")
            return 0

        if not text:
            continue

        if text == "/exit":
            tui.show_info("再见。")
            return 0
        if text == "/help":
            tui.show_help()
            continue
        if text == "/clear":
            session.clear()
            tui.show_info("已清空会话历史。")
            continue

        # 普通提问
        session.add_user(text)
        try:
            reply = tui.render_stream(provider.stream(session.messages()))
        except Exception as e:  # noqa: BLE001  顶层兜底，防崩溃
            tui.show_error(f"{type(e).__name__}: {e}")
            continue
        if reply:
            session.add_assistant(reply)


if __name__ == "__main__":
    sys.exit(main())
