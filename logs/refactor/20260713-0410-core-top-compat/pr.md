# Draft PR：建立官方 core_top 兼容边界

状态：`implementation_in_review / awaiting_push`。不自动创建、标记 ready 或合并 PR。

本 PR 建立精确 49 端口的 SpinalHDL `CoreTopCompat`、锁定工具链的可复现 generator，以及只允许机械改名的 legacy 迁移后端。它固定官方 AXI3/WID、interrupt/debug 和 `aclk/aresetn` 边界，但不声称流水、特权、存储或整机已经迁移。

Pre-commit 已通过 296 项自动化、Scala 4/4、双生成、publish consistency 和 wrapper-only port/lint/Yosys。commit-bound chiplab、Vivado、独立 claim review、失败基线对比和资源影响将在实现提交后补录。回退为 revert 本迭代提交并恢复上一分支 overlay；不自动创建或合并 PR。
