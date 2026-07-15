# Claude 审核结论

- 状态：`unavailable`
- 原因：本地 bridge 缺少 `GEEKPIE_CLAUDE_API_KEY`，reviewer 在启动前失败。
- 处理：保留 Draft，降级为独立只读代码与 claim 审核；不得宣称 Claude 已审核或认可本轮成果。
- 开放项：配置 bridge 后，使用同一 base/head、diff、命令、失败证据和窄化 claim 重新审核。
