# Claude 审核结论

状态：`unavailable`。

本轮先发起允许仓库读取工具的 `claude-review` job，backend 在模型启动前拒绝 reviewer tools。随后把完整相关 diff 内嵌到无工具请求中重试，但因缺少 `GEEKPIE_CLAUDE_API_KEY` 再次在模型启动前失败。两次均没有 Claude 响应、provider、model 或 thread，因此本迭代没有完成 Claude 审核。

处置：

- `CLAUDE-TOOLS-UNAVAILABLE`：`open`，说明带工具的审核没有执行。
- `CLAUDE-CREDENTIAL-UNAVAILABLE`：`open` 且 blocking；Claude required check 不通过。
- 本地独立 Codex 子代理复审只能作为降级只读检查，不能冒充或替代 Claude。
- 迭代保持 `draft`，证据齐全前不创建 PR，不允许状态提升或自动合并。
