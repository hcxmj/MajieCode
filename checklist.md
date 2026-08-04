# MajieCode 交互式对话终端 Checklist

> 每一项通过运行代码或观察行为来验证，聚焦系统行为。

## 实现完整性
- [x] config 模块可加载 YAML 并选出供应商（证据：临时 YAML，`select(None)` 返回 default 条目 ds）
- [x] `${ENV}` 插值生效（证据：`MJ_TEST_KEY=secret123` 时 api_key 被替换为 secret123）
- [x] session 历史管理正确（证据：加两轮后含 system+user+assistant；`clear` 后仅剩 system）
- [x] `create_provider` 按 protocol 分派（证据：openai/anthropic 返回对应实例，非法值抛「未知协议」）
- [x] tui 三种 style 区分渲染（证据：喂 thinking/text/error 事件，分别以思考中/正文/红色错误渲染）

## 集成
- [x] cli 装配链路打通（证据：`python -m majiecode --help` 正常输出）
- [x] OpenAIProvider 真实流式返回（证据：用户关代理后 DeepSeek 端到端验证正常，逐片段出现 text）
- [ ] AnthropicProvider 扩展思考（未验证：本机无 ANTHROPIC_API_KEY；已通过工厂分派与代码审查，用法依 SDK 官方文档）
- [x] 所有公开接口被 cli 主循环真实调用（证据：DeepSeek 一次完整对话跑通）

## 编译与运行
- [x] `python -c "import majiecode"` 无报错（证据：输出版本号 0.1.0）
- [x] 按 `requirements.txt` 在 `.venv` 安装后可 `python -m majiecode` 启动（证据：pip install 成功，启动显示状态行）
- [x] 旧的 `tui/`、`agent/`、`bin/` 已删除（证据：`ls` 已无这些目录）

## 端到端场景（用户手动，关代理后 DeepSeek）
- [x] 场景1 多轮记忆（用户验证：符合预期）
- [x] 场景2 流式输出（用户验证：逐字出现，符合预期）
- [x] 场景3 控制命令 /help /clear /exit（用户验证：符合预期）
- [x] 场景4 切换供应商 --provider（用户验证：符合预期）
- [ ] 场景5 扩展思考（openai 族 reasoner 可自测；anthropic 因无 key 未验）
- [x] 场景6 错误容错（证据：错误 key/超时时显示清晰错误且不崩溃，`❯` 恢复可继续输入）
- [x] 场景7 密钥缺失（同错误处理路径，插值缺失后鉴权失败给出清晰错误）
