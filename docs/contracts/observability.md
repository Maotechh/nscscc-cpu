# Observability 合同

`WritebackStage` 是 `CommitEvent` 的唯一生产者；DiffTest adapter 只消费提交事件和显式
`ArchState`，不得读取流水级内部信号。事件至少覆盖 PC、指令、GPR/CSR 写、异常/ERTN、
load/store、timer 和 TLB 相关状态。

当前 adapter 已接入活动 backend，但 random DiffTest 尚未形成完整通过证据。debug breakpoint
期间架构写入与 commit-valid 的一致性必须通过 directed test 或 ADR 明确，不能用简化 debug
信号替代提交合同。
