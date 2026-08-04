# MajieCode 交互式对话终端 Plan

## 架构概览

分层，自下而上：

- 配置层（config）：加载并校验 YAML，完成 `${ENV}` 插值，按 `default` 或启动参数选出当前 `ProviderConfig`。
- 供应商层（providers）：定义统一接口 `Provider`，屏蔽协议差异；`OpenAIProvider`、`AnthropicProvider` 两个适配器；工厂按 `protocol` 创建实例。对外只吐统一的 `StreamEvent` 流。
- 会话层（session）：维护本次对话的消息历史（系统提示 + 多轮 user/assistant），提供追加、清空、导出为请求 messages 的能力。
- 界面层（tui）：prompt_toolkit 负责输入（行编辑/历史），Rich 负责流式渲染文本与思考（样式区分）；解析 `/exit`、`/clear`、`/help` 控制命令。
- 入口层（cli/main）：解析启动参数，装配各层，驱动「读输入 → 调用 provider → 渲染流」的主循环。

数据流：`用户输入 → session 追加 → provider.stream(messages) → StreamEvent 流 → tui 渲染 → assistant 结果回写 session`。

## 核心数据结构

### ProviderConfig
单个供应商配置：
- `name: str`
- `protocol: str`（`openai` / `anthropic`）
- `model: str`
- `base_url: str`
- `api_key: str`
- `thinking: bool`（默认 False）

### AppConfig
整份配置：
- `default: str`（默认供应商 name）
- `providers: dict[str, ProviderConfig]`
- 方法：`select(name: str | None) -> ProviderConfig`（name 为空时用 default）；构造时校验 default 指向存在。

### Message
- `role: str`（system / user / assistant）
- `content: str`

### StreamEvent
供应商统一输出事件：
- `kind: str`：`thinking` / `text` / `error` / `end`
- `content: str`

### Provider（抽象接口）
- `stream(messages: list[Message]) -> Iterator[StreamEvent]`：给定历史，返回流式事件迭代器；内部负责开/关 thinking、SSE 解析、异常转 `error` 事件、结束发 `end`。

## 模块设计

### config 模块
- 职责：读取 YAML；对每个供应商的 `api_key` 做 `${ENV}` 插值；构造 `AppConfig`；按「启动参数 name > default」确定当前 `ProviderConfig`；校验必填字段与 default 指向存在。
- 对外接口：`load_config(path) -> AppConfig`；`AppConfig.select(name) -> ProviderConfig`。
- 依赖：PyYAML、os.environ。

### providers 模块
- 职责：定义抽象 `Provider` 接口与统一 `StreamEvent`；实现两族适配器；提供工厂。
- `OpenAIProvider`：用 openai SDK，流式读取 `delta.content` 转 `text` 事件；`thinking` 开启时读取 `delta.reasoning_content` 转 `thinking` 事件；异常转 `error`，结束发 `end`。
- `AnthropicProvider`：用 anthropic SDK `messages.stream`，`thinking` 开启时传 `thinking={"type":"enabled","budget_tokens":N}`，事件 `thinking`→`thinking`、`text`→`text`；异常转 `error`，结束发 `end`。
- 工厂：`create_provider(cfg) -> Provider`，按 `cfg.protocol` 分派。
- 依赖：openai、anthropic SDK。

### session 模块
- 职责：维护消息历史。初始化写入系统提示；`add_user` / `add_assistant` 追加；`clear` 重置为仅系统提示；`messages()` 返回请求所需列表。
- 对外接口：`Session`。
- 依赖：无。

### tui 模块
- 职责：渲染与输入。prompt_toolkit 读一行输入（行编辑/上下历史）；Rich 渲染流式 `StreamEvent`：`text` 正常样式、`thinking` 暗淡/斜体、`error` 醒目；输出当前供应商/模型状态；识别控制命令。
- 对外接口：`prompt_user() -> str`；`render_stream(events)`；`show_info/show_error/show_help`。
- 依赖：prompt_toolkit、rich。

### cli/main 模块
- 职责：解析启动参数（`--config`、`--provider`、`--help`）；加载配置、选供应商、建 provider 与 session；驱动主循环；捕获顶层异常。
- 依赖：以上全部模块 + argparse。

## 模块交互

启动：`main` → `config.load_config` → `AppConfig.select(参数)` → `create_provider(cfg)` → 新建 `Session(系统提示)` → `tui.show_info(当前供应商/模型)`。

每轮循环：
1. `tui.prompt_user()` 取输入。
2. 若是 `/exit`/`/clear`/`/help` → 命令处理（退出 / `session.clear` / `tui.show_help`），不调用模型。
3. 否则 `session.add_user(text)` → `provider.stream(session.messages())`。
4. `tui.render_stream(...)` 逐事件渲染，累积 `text` 内容；遇 `error` 事件展示错误。
5. 流结束后 `session.add_assistant(累积文本)`，回到步骤 1。

调用链：`main → tui → session → provider → SDK`；异常在 provider 内转 `error` 事件，main 顶层兜底防崩溃。

## 文件组织

```
MJCode/
├─ majiecode/
│  ├─ __init__.py
│  ├─ __main__.py              # python -m majiecode 启动
│  ├─ cli.py                   # 参数解析 + 装配 + 主循环
│  ├─ config.py                # ProviderConfig/AppConfig、load_config、${ENV} 插值
│  ├─ session.py               # Message、Session
│  ├─ tui.py                   # prompt_toolkit 输入 + Rich 渲染 + 命令
│  └─ providers/
│     ├─ __init__.py           # Provider 抽象、StreamEvent、create_provider 工厂
│     ├─ openai_provider.py    # OpenAIProvider（含 reasoning_content）
│     └─ anthropic_provider.py # AnthropicProvider（extended thinking）
├─ config.example.yaml         # 配置样例
├─ requirements.txt
├─ .gitignore                  # 忽略 config.yaml、.venv 等
└─ README.md
```

> 旧的 `tui/`（Go）、`agent/`、`bin/` 在开发阶段清理。

## 技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 语言/运行 | Python 包 + `python -m majiecode` | 纯 Python；包结构便于扩展 agent 能力 |
| 输入 | prompt_toolkit | 行编辑、上下历史，体验接近 Claude Code |
| 渲染 | Rich（逐事件打印，非全屏 App） | 流式增量输出简单可靠，思考/正文/错误用不同 style 区分 |
| 供应商抽象 | 统一 `Provider.stream → StreamEvent` 迭代器 | 屏蔽协议差异，新增后端只实现一个类，满足 N1 |
| OpenAI 族流式 | SDK 流式 chunk，读 `delta.content` / `delta.reasoning_content` | 兼容 DeepSeek/Qwen/豆包/MiniMax/GLM 的思考字段 |
| Anthropic 思考 | `messages.stream` + `thinking={"type":"enabled","budget_tokens":N}` | 官方扩展思考用法，事件区分 thinking/text |
| thinking 预算 | 内置默认 budget_tokens（如 1600），暂不做成配置项 | YAGNI，spec 只要求开关 |
| 配置选择 | `default` 字段 + `--provider` 覆盖 | 对应 F5 |
| 密钥安全 | `${ENV}` 插值；`config.yaml` 入 .gitignore | 对应 N4 |
| 错误处理 | provider 内异常转 `error` 事件 + main 顶层兜底 | 对应 N3 |
| 同步 vs 异步 | 同步实现 | 单用户串行，无需异步复杂度 |
