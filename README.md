# MajieCode

运行在终端里的 AI 编程助手（类 Claude Code），纯 Python 实现。

本阶段为**交互式对话终端**：启动后进入 TUI，输入问题，模型回复流式逐字打印，支持多轮上下文记忆。通过 YAML 配置管理多家 LLM 供应商，支持 Claude 扩展思考。暂不含工具调用、文件操作等 agent 能力。

## 特性

- 交互式终端对话（prompt_toolkit 输入 + Rich 渲染）
- 流式（SSE）逐字增量输出
- 多轮上下文记忆（仅当前会话内存保留）
- 多供应商配置，统一抽象接口，两族协议：`openai`（兼容 DeepSeek/Qwen/豆包/MiniMax/GLM/OpenAI）与 `anthropic`
- 支持 Claude extended thinking，思考过程样式区分实时展示
- `api_key` 支持 `${ENV_VAR}` 环境变量插值

## 目录结构

```
MJCode/
├─ majiecode/
│  ├─ __main__.py              # python -m majiecode 启动
│  ├─ cli.py                   # 参数解析 + 装配 + 主循环
│  ├─ config.py                # 配置加载、${ENV} 插值、供应商选择
│  ├─ session.py               # 会话历史管理
│  ├─ tui.py                   # 输入 + 流式渲染 + 命令
│  └─ providers/               # 供应商抽象与适配器
│     ├─ __init__.py           # Provider / StreamEvent / create_provider
│     ├─ openai_provider.py
│     └─ anthropic_provider.py
├─ config.example.yaml
└─ requirements.txt
```

## 安装

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 配置

复制样例并按需修改（`config.yaml` 已被忽略，不会入库）：

```bash
cp config.example.yaml config.yaml
```

在 `config.yaml` 中用顶层 `default` 指定默认供应商。密钥推荐用环境变量插值：

```yaml
api_key: ${DEEPSEEK_API_KEY}
```

对应地在 shell 里导出：

```bash
export DEEPSEEK_API_KEY=你的密钥
```

## 启动

```bash
.venv/bin/python -m majiecode                 # 用 default 供应商
.venv/bin/python -m majiecode --provider claude   # 临时切换供应商
.venv/bin/python -m majiecode --config other.yaml # 指定配置文件
```

## 交互命令

| 命令 | 作用 |
|------|------|
| `/help` | 显示帮助 |
| `/clear` | 清空当前会话历史 |
| `/exit` | 退出（Ctrl+C 亦可） |

其余输入作为提问发送给模型。

## 扩展新供应商

- 同族后端（openai/anthropic）：在 `config.yaml` 增加一条配置即可。
- 全新协议：在 `majiecode/providers/` 实现一个 `Provider` 子类，并在 `create_provider` 中注册。
