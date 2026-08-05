# MajieCode 工具系统 Plan

## 架构概览

在现有分层（config / session / providers / tui / cli）之上新增 tools 层，并小幅扩展 session、providers、cli。

- tools 层（新增）：工具抽象与结构化结果、六个具体工具、注册中心、路径安全模块。
- session 层（扩展）：Message 升级为可承载工具调用（assistant）与工具结果（tool 角色）的富消息；新增追加方法。
- providers 层（扩展）：StreamEvent 增加工具调用事件；ToolCall 结构；Provider.stream() 增加 tools 参数；两族适配器负责富消息转 payload、拼接工具调用 JSON 碎片、流末产出完整 ToolCall。
- tui 层（扩展）：render_stream 返回文本与工具调用列表；新增展示工具调用与结果摘要的方法。
- cli 层（扩展）：主循环在流结束后，若存在工具调用则执行工具、回灌历史、展示结果，然后停。

数据流：用户输入 → cli → provider.stream(历史, 工具声明) → 流式 text + 末尾 ToolCall → cli 执行工具 → ToolResult → 回灌 Message 历史 → 展示 → 停。

## 核心数据结构

- ToolParam：name、type（JSON Schema 类型）、description、required=True。
- ToolResult：ok、output、error；类方法 success/fail；to_model_text()。
- Tool(ABC)：name、description、parameters；run(args)->ToolResult；input_schema()。
- ToolCall：id、name、arguments(dict)。
- StreamEvent（扩展）：kind（thinking/text/tool_call/error/end）、content、tool_call。
- Message（扩展）：role、content、tool_calls、tool_call_id、name。
- ExecContext：workdir（工作目录绝对路径）。

## 模块设计

- tools/base.py：ToolParam / ToolResult / Tool / ExecContext。
- tools/safety.py：resolve_in_workdir(workdir, path)（realpath + commonpath 校验）、PathEscapeError。
- tools/filesystem.py：ReadFileTool / WriteFileTool / EditFileTool。
- tools/shell.py：RunCommandTool（subprocess.run，shell=True，cwd=workdir，timeout）。
- tools/search.py：GlobTool（glob 递归）/ GrepTool（os.walk + re，跳过二进制/超大文件，命中上限）。
- tools/registry.py：Registry（register/get/all、to_openai_schema、to_anthropic_schema）、build_default_registry(ctx)。
- session.py：add_assistant(content, tool_calls=None)、add_tool_result(tool_call_id, name, output)。
- providers/__init__.py：ToolCall、StreamEvent.tool_call、Provider.stream(messages, tools=None)。
- providers/openai_provider.py：payload 构造（assistant.tool_calls / role=tool）、请求带 tools、按 index 拼接 delta.tool_calls、流末产出 ToolCall。
- providers/anthropic_provider.py：payload 构造（tool_use / tool_result block）、请求带 tools、content_block 事件累积 partial_json、块结束产出 ToolCall。
- tui.py：render_stream 返回 (text, tool_calls)、show_tool_call、show_tool_result。
- cli.py：ExecContext(os.getcwd()) + build_default_registry；主循环执行工具、回灌、展示、停。

## 模块交互

装配：os.getcwd() → ExecContext → build_default_registry → Registry；create_provider → Provider。

主循环：add_user → 选 tools(按 protocol) → provider.stream → (reply, tool_calls) → 若有调用：add_assistant(reply, tool_calls)，逐个 show_tool_call → registry.get → run → show_tool_result → add_tool_result；停。否则 add_assistant(reply)。

调用链无环：cli → registry/provider/tui；registry → tools/*；tools/* → base/safety；providers → session(Message)/base(ToolCall)。

## 文件组织

```
majiecode/
├─ cli.py                     # 装配 registry，主循环执行工具+回灌
├─ session.py                 # 富 Message、add_tool_result
├─ tui.py                     # render_stream 返回 tool_calls，show_tool_*
├─ providers/
│  ├─ __init__.py             # StreamEvent.tool_call、ToolCall、stream(tools=)
│  ├─ openai_provider.py      # tool_calls 解析/payload/请求带 tools
│  └─ anthropic_provider.py   # tool_use 解析/payload/请求带 tools
└─ tools/
   ├─ __init__.py             # 导出主要类型
   ├─ base.py                 # ToolParam / ToolResult / Tool / ExecContext
   ├─ safety.py               # resolve_in_workdir / PathEscapeError
   ├─ filesystem.py           # ReadFileTool / WriteFileTool / EditFileTool
   ├─ shell.py                # RunCommandTool
   ├─ search.py               # GlobTool / GrepTool
   └─ registry.py             # Registry / build_default_registry / 两族导出
```

## 技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 工具调用如何出流 | 复用 StreamEvent，新增 tool_call kind + tool_call 字段 | 不破坏现有迭代器契约 |
| JSON 碎片拼接位置 | Provider 内部累积，流末产出完整 ToolCall | 上层拿到的永远是完整调用 |
| 工作目录注入 | 构造 ExecContext 注入工具实例 | 安全校验集中 |
| 路径越界判定 | realpath + commonpath 比对 workdir | 防 ..、符号链接与绝对路径逃逸 |
| 改文件匹配 | 纯字符串 count==1 才替换 | 契合唯一匹配，0/多次给明确错误 |
| 命令执行 | subprocess.run(shell=True, cwd, timeout) | 捕获 stdout/stderr/退出码 + 超时 |
| 搜索/找文件 | os.walk/glob/re 纯标准库 | 零重型依赖、跨平台 |
| 结果回灌格式 | openai 用 role=tool；anthropic 用 tool_result block | 贴合两族 API 契约 |
| 单轮即停 | 回灌后不再请求模型 | 契合本章边界 |
