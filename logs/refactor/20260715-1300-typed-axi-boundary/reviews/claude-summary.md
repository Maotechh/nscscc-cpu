# Claude 审核摘要

- 状态：`unavailable`
- 原因：运行环境缺少 `GEEKPIE_CLAUDE_API_KEY`，bridge 在审核开始前失败。
- 处理：保留原始错误；降级为独立只读代码审查，单独写入 `independent-review.md`，不得称为 Claude 审核。
- Claim 约束：PR 保持 draft；不声明完整行为等价、功能完整或 release ready。
