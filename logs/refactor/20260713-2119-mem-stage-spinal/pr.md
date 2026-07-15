# Draft PR: refactor MEM stage to typed SpinalHDL

状态：`awaiting_pr` draft；分支已推送，未创建 PR。Claude bridge tool error，独立降级审查仅支持 scoped leaf claim；活动集成与官方影响矩阵门禁未完成，不得自动合并。

## 行为合同

将 `a158aa8:rtl/mem_stage.v` 的 49 端口与逐周期状态行为迁移为 typed `MemoryStage` + legacy `LegacyMemoryStage`。公开 legacy 总线位宽保持 425/493/39，内部以 `Stream[ExecutePayload]`、`Stream[MemoryPayload]` 和明确控制字段连接。

## 验证

Scala 4/4、Python 333、reproducible generate 2/2、49/49 contract/port、lint、Yosys、8248-cycle lockstep 和负控均通过。五类 flush 已逐项 directed 覆盖；详见 `logs/refactor/20260713-2119-mem-stage-spinal/`。

## 未完成与风险

尚未进入活动 overlay，未运行官方 func、58/81、random、perf、Linux 或 Vivado。当前 claim 仅限 MEM 叶子 differential pass；官方 baseline 的 `0x1c07c79c` mismatch 仍未解决。

## 回退

revert 本 PR；当前稳定 overlay 未引用该 replacement spec。
