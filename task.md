# MajieCode 工具系统 Tasks

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `majiecode/tools/__init__.py` | 导出工具系统主要类型 |
| 新建 | `majiecode/tools/base.py` | ToolParam / ToolResult / Tool / ExecContext |
| 新建 | `majiecode/tools/safety.py` | resolve_in_workdir / PathEscapeError |
| 新建 | `majiecode/tools/filesystem.py` | ReadFileTool / WriteFileTool / EditFileTool |
| 新建 | `majiecode/tools/shell.py` | RunCommandTool |
| 新建 | `majiecode/tools/search.py` | GlobTool / GrepTool |
| 新建 | `majiecode/tools/registry.py` | Registry / build_default_registry / 两族导出 |
| 修改 | `majiecode/providers/__init__.py` | ToolCall、StreamEvent.tool_call、stream(tools=) |
| 修改 | `majiecode/session.py` | 富 Message、add_assistant(tool_calls)、add_tool_result |
| 修改 | `majiecode/providers/openai_provider.py` | tool_calls 解析/payload/请求带 tools |
| 修改 | `majiecode/providers/anthropic_provider.py` | tool_use 解析/payload/请求带 tools |
| 修改 | `majiecode/tui.py` | render_stream 返回 tool_calls、show_tool_* |
| 修改 | `majiecode/cli.py` | 装配 registry、主循环执行工具+回灌 |

## T1: 工具抽象与结构化结果（tools/base.py）
定义 ToolParam、ToolResult（success/fail/to_model_text）、ExecContext、Tool(ABC，run + input_schema)。
验证：`ToolResult.fail('x').to_model_text()` == `错误：x`。

## T2: 路径越界校验（tools/safety.py）
PathEscapeError；resolve_in_workdir 用 realpath + commonpath 校验。
验证：越界路径抛 PathEscapeError。

## T3: 文件工具（tools/filesystem.py，依赖 T1/T2）
ReadFileTool / WriteFileTool / EditFileTool（唯一匹配替换三态）。
验证：写→读一致；edit 唯一成功、无匹配/多处报错。

## T4: 命令执行工具（tools/shell.py，依赖 T1）
RunCommandTool：subprocess.run + 超时；返回退出码/stdout/stderr。
验证：echo hi 含 hi；sleep 5 + timeout=1 返回超时。

## T5: 检索工具（tools/search.py，依赖 T1/T2）
GlobTool / GrepTool（纯标准库，跳过二进制/超大，命中上限）。
验证：**/*.py 列出文件；grep 命中含路径:行号:行文本；无命中返回提示。

## T6: 富消息模型（session.py，依赖 T7）
Message 增 tool_calls/tool_call_id/name；add_assistant(tool_calls)、add_tool_result。
验证：messages() 含带 tool_calls 的 assistant 与 role=tool 消息。

## T7: providers 类型扩展（providers/__init__.py）
ToolCall；StreamEvent.tool_call；Provider.stream(messages, tools=None)。
验证：构造 StreamEvent('tool_call', tool_call=ToolCall(...)) 可读 name。

## T8: OpenAI 族工具支持（openai_provider.py，依赖 T6/T7）
payload 构造（assistant.tool_calls / role=tool）；请求带 tools；按 index 拼接 delta.tool_calls；流末产出 ToolCall。
验证：编译通过；端到端见 checklist。

## T9: Anthropic 族工具支持（anthropic_provider.py，依赖 T6/T7）
payload 构造（tool_use / tool_result block）；请求带 tools；content_block 事件累积 partial_json 并产出 ToolCall。
验证：编译通过。

## T10: TUI 展示（tui.py，依赖 T7）
render_stream 返回 (text, tool_calls)；show_tool_call、show_tool_result。
验证：喂含 tool_call 的事件，返回 tool_calls 正确。

## T11: 注册中心（tools/registry.py + __init__.py，依赖 T1/T3/T4/T5）
Registry（register/get/all、两族导出）；build_default_registry 登记 6 工具。
验证：get 6 个工具非空；两族 schema 各 6 项、字段正确。

## T12: CLI 接入（cli.py，依赖 T10/T11/T6）
ExecContext(os.getcwd()) + registry；主循环按 protocol 选 tools，执行工具、回灌、展示、单轮即停。
验证：`python -m majiecode` 启动无报错；端到端见 checklist。

## 执行顺序
T1 → T2 → T7 → T6 → T3 → T4 → T5 → T8 → T9 → T10 → T11 → T12。
