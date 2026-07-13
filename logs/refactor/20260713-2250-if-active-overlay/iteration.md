# 20260713-2250-if-active-overlay

- 状态：`draft`，正在执行门禁。
- 分支 / Base SHA / Head SHA：`refactor/20260713-2250-if-active-overlay` / `95da435a537703c091fa97bf6b4d352255207556` / 待提交。
- 负责人：Codex `/root/if_stage_spinal`。
- 选择边界：把已完成隔离差分的 `if_stage` replacement 接入活动 reachable overlay；基线包含 MEM overlay，但本分支不改动 MEM 实现。
- 锁定事实源：golden `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/if_stage.v`；chiplab `a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`；Vivado 2023.2；Scala 2.13.16 / SpinalHDL 1.14.2 / Verilator 5.020。
- 行为合同：`docs/contracts/if-stage.md` 与 `reference/component-replacements/if-stage.json`。
- 修改范围：active replacement spec/meta、status、reachability test 和本迭代证据。
- 尝试与失败：待记录。
- Gate 结果：待记录。
- 未执行：58/81、multi-seed random DiffTest、perf20、U-Boot/Linux、Vivado implementation/timing/bitstream、完整顺序形式等价。
- 回退：revert 本迭代提交即可从 active overlay 移除 IF；保留 IF leaf 分支。
- PR：`awaiting_push`；不自动创建或合并。
