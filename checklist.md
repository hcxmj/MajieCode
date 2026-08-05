# MajieCode 工具系统 Checklist

> 每一项通过运行代码或观察行为来验证，聚焦系统行为。

## 实现完整性
- [x] 工具抽象可用：实例化任一工具能读到 name/description/parameters，input_schema() 生成合法 JSON Schema。（AC1）
- [x] ToolResult：success/fail 与 to_model_text() 行为正确（fail('x') → 错误：x）。（AC11）
- [x] 读文件：读工作目录内文本返回内容；读不存在路径返回结构化失败而非崩溃。（AC3）
- [x] 写文件：写入含新建子目录的新路径文件被创建且内容正确；覆盖生效。（AC4）
- [x] 改文件三态：唯一匹配替换成功；无匹配「未匹配」；多处「匹配多处」，失败均不改文件。（AC5）
- [x] 执行命令：返回 stdout/stderr/退出码；sleep + 小 timeout 返回超时失败。（AC6）
- [x] 找文件：glob **/*.py 列出 py 文件；无匹配返回提示而非报错。（AC7）
- [x] 搜内容：grep 返回「路径:行号:行文本」；无命中返回提示。（AC8）

## 集成
- [x] 注册中心按名查找：build_default_registry 后 6 个工具 get 均非空。（AC1）
- [x] 两族导出：to_openai_schema 每项含 type/function{name,description,parameters}；to_anthropic_schema 每项含 name/description/input_schema；均 6 项。（AC2）
- [x] 富消息回灌：add_assistant(reply, tool_calls) 与 add_tool_result 后 messages() 依次出现带 tool_calls 的 assistant 与 role=tool 消息。（AC12）
- [x] 流事件收集：含 tool_call 的 StreamEvent 序列经 render_stream，返回的 tool_calls 数量与内容正确。（AC10）
- [x] 越界防护：../ 越界或绝对逃逸路径调用文件/命令工具均返回越界失败且未实际读写。（AC9）
- [x] 未知工具容错：registry.get('不存在') 为 None，主循环返回「未知工具」失败而非崩溃。（AC11）

## 编译与运行
- [x] 全部模块导入无错：import cli/tools.registry/两个 provider/tui 成功。
- [x] 程序可启动：python -m majiecode 进入交互界面并接受输入。
- [x] 向后兼容：不触发工具的普通提问仍能流式回复并入历史。

## 端到端场景（tmux）
- [x] 场景1 读文件：请模型「读取 README.md 并概述」，观察到 read_file 调用 → 执行 → 回灌 → 结束，无崩溃。（AC13）
- [x] 场景2 单轮即停：工具执行完后停在等待输入，未自动发起下一次模型请求。（AC12）
- [x] 场景3 失败可恢复：edit 未匹配本地验证通过；tmux 中工具失败/API 超时后程序继续可用。（AC11/AC5）
