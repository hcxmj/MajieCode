"""配置层：加载 YAML、环境变量插值、选择当前供应商。"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import yaml

# 匹配 ${ENV_VAR} 形式的占位符
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigError(Exception):
    """配置相关的错误。"""


@dataclass
class ProviderConfig:
    """单个供应商配置。"""

    name: str
    protocol: str
    model: str
    base_url: str
    api_key: str
    thinking: bool = False


@dataclass
class AppConfig:
    """整份配置：默认供应商 + 所有供应商条目。"""

    default: str
    providers: dict[str, ProviderConfig] = field(default_factory=dict)

    def select(self, name: str | None) -> ProviderConfig:
        """按 name 选供应商；name 为空时用 default。"""
        target = name or self.default
        cfg = self.providers.get(target)
        if cfg is None:
            available = ", ".join(self.providers) or "（无）"
            raise ConfigError(f"找不到供应商 '{target}'，可用：{available}")
        return cfg


def _interpolate_env(value: str) -> str:
    """把字符串里的 ${ENV_VAR} 替换成环境变量值；缺失则保留原样以便后续报错。"""

    def repl(m: re.Match) -> str:
        return os.environ.get(m.group(1), m.group(0))

    return _ENV_PATTERN.sub(repl, value)


def load_config(path: str) -> AppConfig:
    """读取并校验 YAML 配置文件。"""
    if not os.path.exists(path):
        raise ConfigError(f"配置文件不存在：{path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ConfigError("配置文件格式错误：顶层应为映射")

    default = raw.get("default")
    if not default:
        raise ConfigError("配置缺少 default 字段")

    raw_providers = raw.get("providers")
    if not isinstance(raw_providers, list) or not raw_providers:
        raise ConfigError("配置缺少 providers 列表或为空")

    providers: dict[str, ProviderConfig] = {}
    for item in raw_providers:
        if not isinstance(item, dict):
            raise ConfigError("providers 中每项应为映射")
        name = item.get("name")
        if not name:
            raise ConfigError("某个供应商缺少 name 字段")

        protocol = item.get("protocol")
        if protocol not in ("openai", "anthropic"):
            raise ConfigError(
                f"供应商 '{name}' 的 protocol 非法（应为 openai 或 anthropic）：{protocol}"
            )

        for required in ("model", "base_url", "api_key"):
            if not item.get(required):
                raise ConfigError(f"供应商 '{name}' 缺少 {required} 字段")

        providers[name] = ProviderConfig(
            name=name,
            protocol=protocol,
            model=item["model"],
            base_url=item["base_url"],
            api_key=_interpolate_env(str(item["api_key"])),
            thinking=bool(item.get("thinking", False)),
        )

    if default not in providers:
        raise ConfigError(f"default 指向的供应商 '{default}' 不在 providers 中")

    return AppConfig(default=default, providers=providers)
