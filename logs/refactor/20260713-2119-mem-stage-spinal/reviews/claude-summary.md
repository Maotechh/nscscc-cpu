# Claude review 中文结论

- 状态：`tool_error`
- 原因：环境缺少 `GEEKPIE_CLAUDE_API_KEY`，job 在开始评审前失败。
- 处理：不接受任何外部审查 claim；PR 保持 draft，改做独立只读审查。
- Open: 恢复 Claude bridge 后应针对同一 base/head 与 evidence 重新调用。
