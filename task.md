# MajieCode 交互式对话终端 Tasks

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `requirements.txt` | 依赖声明 |
| 新建 | `.gitignore` | 忽略 config.yaml/.venv 等 |
| 新建 | `majiecode/__init__.py`、`__main__.py` | 包与启动入口 |
| 新建 | `majiecode/config.py` | 配置加载、插值、选择 |
| 新建 | `majiecode/session.py` | Message、Session |
| 新建 | `majiecode/providers/__init__.py` | Provider 抽象、StreamEvent、工厂 |
| 新建 | `majiecode/providers/openai_provider.py` | OpenAI 兼容族适配器 |
| 新建 | `majiecode/providers/anthropic_provider.py` | Anthropic 适配器 |
| 新建 | `majiecode/tui.py` | 输入 + 流式渲染 + 命令 |
| 新建 | `majiecode/cli.py` | 参数解析 + 装配 + 主循环 |
| 新建 | `config.example.yaml` | 配置样例 |
| 重写 | `README.md` | 使用说明 |
| 删除 | `tui/`、`agent/`、`bin/` | 清理旧实现 |

## T1: 项目骨架与依赖
**文件：** `requirements.txt`、`.gitignore`、`majiecode/__init__.py`、`majiecode/__main__.py`、`majiecode/providers/__init__.py`（占位）
**依赖：** 无
**步骤：**
1. `requirements.txt` 写入 pyyaml、openai、anthropic、prompt_toolkit、rich。
2. `.gitignore` 忽略 `config.yaml`、`.venv/`、`__pycache__/`、`*.pyc`。
3. 建 `majiecode/` 与 `majiecode/providers/` 包目录及 `__init__.py`。
4. `__main__.py` 调用 `cli.main()`（先留导入占位）。
**验证：** `python -c "import majiecode"` 无报错。

## T2: config 模块
**文件：** `majiecode/config.py`
**依赖：** T1
**步骤：**
1. 定义 `ProviderConfig`（六字段，thinking 默认 False）、`AppConfig`（default + providers dict）。
2. `load_config(path)`：读 YAML，遍历 providers，对 `api_key` 做 `${ENV}` 插值（缺失环境变量时保留标记以便后续报错）。
3. `AppConfig.select(name)`：name 为空用 default；找不到抛清晰异常。
4. 校验 default 指向存在、必填字段非空。
**验证：** 写一个临时 YAML，`load_config` 后 `select(None)` 返回 default 供应商；`${ENV}` 被正确替换。

## T3: session 模块
**文件：** `majiecode/session.py`
**依赖：** T1
**步骤：**
1. 定义 `Message`（role、content）。
2. `Session(system_prompt)`：初始化含系统提示；`add_user`/`add_assistant`/`clear`/`messages()`。
**验证：** 新建 Session，加两轮消息，`messages()` 返回含 system 的完整列表；`clear` 后仅剩 system。

## T4: providers 抽象层
**文件：** `majiecode/providers/__init__.py`
**依赖：** T1
**步骤：**
1. 定义 `StreamEvent`（kind、content）与抽象 `Provider.stream(messages)`。
2. `create_provider(cfg)`：按 `protocol` 分派到两个适配器；未知协议抛异常。
**验证：** `create_provider` 对 `openai`/`anthropic` 返回对应实例，非法值报错。

## T5: OpenAIProvider
**文件：** `majiecode/providers/openai_provider.py`
**依赖：** T2、T4
**步骤：**
1. 用 `base_url`/`api_key` 建 OpenAI 客户端。
2. 流式请求，逐 chunk：`delta.content`→`text` 事件；`thinking` 开启且有 `delta.reasoning_content`→`thinking` 事件。
3. 异常转 `error` 事件，最后发 `end`。
**验证：** 用可用的 openai 兼容 key 提问，能看到流式 `text` 事件（可在 tmux 端到端阶段验）。

## T6: AnthropicProvider
**文件：** `majiecode/providers/anthropic_provider.py`
**依赖：** T2、T4
**步骤：**
1. 用 `base_url`/`api_key` 建 Anthropic 客户端。
2. `messages.stream`，`thinking` 开启时传 `thinking={"type":"enabled","budget_tokens":1600}`（并满足 max_tokens 约束）。
3. 事件 `thinking`→`thinking`、`text`→`text`；异常转 `error`，最后 `end`。
**验证：** 用 Claude key 开 thinking 提问，先出 `thinking` 后出 `text`。

## T7: tui 模块
**文件：** `majiecode/tui.py`
**依赖：** T3、T4
**步骤：**
1. `prompt_user()`：prompt_toolkit 读一行，带上下历史。
2. `render_stream(events)`：逐事件用 Rich 打印，`thinking` 暗淡/斜体、`text` 正常、`error` 醒目；返回累积正文。
3. `show_info/show_error/show_help`；命令识别 `/exit`、`/clear`、`/help`。
**验证：** 手动喂一串 StreamEvent，观察不同 style 渲染；输入 `/help` 显示帮助文本。

## T8: cli 主循环
**文件：** `majiecode/cli.py`
**依赖：** T2、T5、T6、T7
**步骤：**
1. argparse：`--config`（默认 `config.yaml`）、`--provider`。
2. 装配：load_config → select → create_provider → Session。
3. 主循环：prompt_user → 命令分支 / 调用 provider.stream → render_stream → add_assistant；顶层 try 兜底。
4. 启动打印当前供应商/模型。
**验证：** `python -m majiecode --help` 正常；配置就绪时能进入交互界面。

## T9: 配置样例、文档与清理
**文件：** `config.example.yaml`、`README.md`；删除 `tui/`、`agent/`、`bin/`
**依赖：** T8
**步骤：**
1. `config.example.yaml`：写 default + 两族示例（含 `${ENV}` 用法、thinking 开关）。
2. 重写 `README.md`：安装、配置、启动、命令、切换供应商说明。
3. 删除旧的 `tui/`、`agent/`、`bin/`。
**验证：** 按 README 从 `config.example.yaml` 复制出 `config.yaml` 可启动。

## 执行顺序
```
T1 → T2 → T3 → T4 → {T5, T6, T7} → T8 → T9
```
