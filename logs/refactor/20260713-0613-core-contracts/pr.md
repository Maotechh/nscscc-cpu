# Draft PR：冻结整机 typed contracts

状态：`implementation_in_review / awaiting_push`。不自动创建、标记 ready 或合并 PR。

本 PR 只建立公共配置与合同，不切换活动 backend，不宣称流水、特权、存储或 DiffTest 已迁移。

- 行为合同：directionless payload、显式 Stream/Flow ownership、locked LACC/DiffTest matrix、AXI3/WID、CommitEvent/ArchState。
- 验证：doctor 19/19；Scala 4/4、18 tests、0 skip；golden parser 8/8；POSIX automation 304/304、0 skip。
- 性能/资源：活动 backend 未变，未运行功能、perf 或 Vivado implementation，不声称增量。
- 回退：revert 本 prerequisite PR。
- 风险：Claude bridge unavailable；WB breakpoint 的 golden level-side-effect 冲突留待独立 ADR。
- 日志：`logs/refactor/20260713-0613-core-contracts/iteration.md`。
