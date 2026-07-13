# 20260713-2250-if-active-overlay

- 状态：`draft`；官方 smoke 失败，禁止标记 ready。
- 分支 / Base SHA / Head SHA：`refactor/20260713-2250-if-active-overlay` / `95da435a537703c091fa97bf6b4d352255207556` / `f0b5e2410fccba7c69f143dabed3e50da841b5b4`（clean source commit）。
- 负责人：Codex `/root/if_stage_spinal`。
- 选择边界：把已完成隔离差分的 `if_stage` replacement 接入活动 reachable overlay；基线包含 MEM overlay，本分支不修改 MEM leaf 或已有 replacement blob。
- 锁定事实源：golden `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/if_stage.v`；chiplab `a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`；myCPU gitlink `aa3bde1f3e720e71c2c78d6b81930d797b810149`；Scala 2.13.16 / SpinalHDL 1.14.2 / Verilator 5.020。
- 行为合同：`docs/contracts/if-stage.md` 与 `reference/component-replacements/if-stage.json`。
- 修改文件：active replacement spec/meta、status、reachability test 和本目录日志/证据；IF leaf 源与 replacement 由已审核分支 cherry-pick。
- 尝试与失败：cherry-pick 在 status.yml 冲突，人工保留 writeback/memory 并加入独立 IF 条目；Claude job `6962eeba98f34f4a888c13ab6d3f7638` 因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败；官方 smoke 严格失败。
- Gate 结果：reachability 13/13 PASS；Scala 4/4 PASS；WSL automation 333/333 PASS；Windows pytest 323 passed/10 platform skips；locked doctor PASS；clean diagnostic overlay 接受 13 committed replacements但 `gate_eligible=false`；official func_lab19 0/1 FAIL。
- 官方 smoke：instruction `172552`，PC `0x1c07c79c`，`t0/r12` right `0x000006e2` vs wrong `0x00000008`；trace SHA256 `8efa7942ab6d4702129dc0c7eb0676c6cfcd87361ee8ecf99411567c3db38acb` 与锁定 baseline/MEM overlay 相同；仅支持“本 trace 未观察到更早可见分歧”。
- Warning：245 个 DUT warning、373 个官方环境 warning，均无逐条批准 waiver，构成 smoke 失败原因。
- 未执行：58/81、multi-seed random DiffTest、perf20、U-Boot/Linux、Vivado implementation/timing/bitstream、完整顺序形式等价。
- 残余风险：legacy Verilog backend 仍活动；diagnostic overlay 不是正式 gate；单 trace 不能证明集成等价；Claude bridge 不可用。
- 回退：revert `f0b5e2410fccba7c69f143dabed3e50da841b5b4` 及本迭代证据提交，从 active overlay 移除 IF；MEM baseline 保持不变。
- PR：`awaiting_push`；提交并推送分支，不创建或合并 PR。
