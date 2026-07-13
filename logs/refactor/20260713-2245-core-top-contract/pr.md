# PR 草稿：复核 core_top compatibility contract

- Branch：`refactor/20260713-2245-core-top-contract`
- Base：`b2946f8ac93fc9ccfa9c8748bb53f444976c36cb`
- Scope：只读复核锁定 `core_top` 的端口、时钟/reset、AXI/debug 和现有自动化；不修改 RTL/Scala/overlay。
- Evidence：`logs/refactor/20260713-2245-core-top-contract/`。
- 支持声明：锁定 49 端口合同、可复现 wrapper、49/49 同名连接和 wrapper-only 静态门禁通过。
- 明确不声明：整机功能、reset 状态等价、AXI/debug 事务语义、58/81、random、perf、Linux、Vivado implementation 或完全重构。
- Review：Claude bridge 缺少 API key；保留原始错误并执行独立本地只读审核。
- Rollback：revert 本日志 PR；代码和 overlay 无变化。
- 状态：仅推送分支，等待维护者手工创建 draft PR；不自动 merge。
