# Draft PR：以 SpinalHDL 重构 openLA500 mul 叶子

状态：`awaiting_implementation_commit`。本分支 stacked 在
`refactor/20260712-1600-mul-harness`；不自动创建、标记 ready 或合并。

## 目标与合同

只迁移 `a158aa8:rtl/mul.v` 的当前活动行为：精确六端口、显式 `mul_clk`
ClockDomain、同步 reset-hold，以及沿后可见的 64-bit signed/unsigned 乘积。

## 验证

Pre-commit 已执行 192 项自动化、Scala 4 项、双生成、port/lint/Yosys、4128
cycle differential、candidate contract formal 和 Vivado 叶子综合。实现提交后将全部重跑并
执行官方 chiplab mixed overlay；当前报告不得冒充 commit-bound 证据。

Vivado 只完成叶子 synth，candidate 有 63 条未批准 warning；golden 完整 formal 等价仍因
solver timeout 未证明。两项都必须在 PR 中保持公开。

## 非目标与回退

不修改 decode、pipeline、cache、CSR、AXI 或性能策略；不声明整机、Linux、完整功能集、
Fmax 或完全重构。回退方式为 revert 本迭代提交并继续使用原 `rtl/mul.v`。
