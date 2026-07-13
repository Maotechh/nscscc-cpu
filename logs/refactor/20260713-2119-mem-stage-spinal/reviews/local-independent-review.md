# MEM stage 独立只读审查

审查范围：`b2946f8..81bb0c4`、锁定 `a158aa8:rtl/mem_stage.v`、gate 与结构化 evidence。审查者为独立 Codex 子代理；不是 Claude。

## Blocking（仅针对 ready/合入）

1. 活动 overlay、官方 func-full/random、存储随机 backpressure/delay、perf 等 change-impact gate 未完成，因此不能提升到 `integrated_pass` 或 ready。
2. Claude bridge 没有产生响应，不能声明 Claude 审核通过。

## 已修复发现

1. 原 testbench 只 directed 驱动 `excp_flush`。现已逐项驱动 `excp/ertn/refetch/icacop/idle`，并与新 input、`data_data_ok` 和 `ws_allowin=0` 同周期组合，重跑 8248 cycles PASS。
2. 三项 candidate warning 原仅在 component contract 中精确列出。现已同步到 `lint-waivers.yml`，包含文件/行、candidate hash、reason、owner 和到期条件；gate 会校验中心 waiver 与 candidate hash。

## Open

- 单个固定 seed、2-state Verilator 和 `x=0` 不能证明全输入或未初始化状态等价；必须保持轨迹范围 claim。
- evidence follow-up commit 与 reviewed source SHA 必须在 PR 元数据中分别列出。

## RTL 与 gate 结论

未发现 code-level blocking 时序差异。allow/valid/data buffer/input replacement/flush 优先级、DMW/TLB 异常位序、load/mul/div/SC OR 语义、forward/stall/`ms_flush` 均与 golden 对应。gate 比较全部 15 输出、每周期 3 phase；负控在 cycle 3 检出。

允许的最窄 claim：`81bb0c4` 的 MEM 叶子在锁定 a158aa8 oracle、固定 seed `0x0158aa8d`、8248-cycle directed/random 2-state Verilator 轨迹与静态合同范围内达到 `differential_pass`。
