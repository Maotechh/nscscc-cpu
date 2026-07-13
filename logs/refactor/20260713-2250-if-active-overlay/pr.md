# PR 草稿（不自动创建）

标题：`refactor: add Spinal IF stage to active replacement overlay`

状态：`awaiting_push`。本分支只通过人工评审后合入，代理不创建或合并 PR。

范围：在固定 MEM overlay 基线之上，将已完成隔离差分的 `if_stage` 作为第 13 个 reachable replacement；不修改 MEM leaf 或其他 replacement blob。

证据：reachability 13/13、Scala 4/4、WSL automation 333/333、locked doctor 均通过；clean diagnostic overlay 接受 13 个 committed blob，但明确 `gate_eligible=false`。官方 func_lab19 严格 FAIL：0/1、首错 `0x1c07c79c`、245 个 DUT warning、373 个环境 warning。trace 与 baseline 一致只说明未观察到更早分歧，不构成功能或集成通过。

限制：不声明 58/81、random DiffTest、性能、Linux、Vivado、整机等价、`integrated_pass` 或完全重构。Claude bridge 失败，等待独立只读和人工审核。

回退：revert 本迭代 source/evidence 提交即可移除 IF active replacement，MEM baseline 不变。
