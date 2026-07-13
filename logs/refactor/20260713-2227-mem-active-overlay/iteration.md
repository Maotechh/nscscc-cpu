# 20260713-2227-mem-active-overlay

- 状态：implementation_in_review；官方 smoke 失败，保持 draft。
- 分支 / Base SHA / Head SHA：`refactor/20260713-2227-mem-active-overlay` / `da44b6dea9d3b5adefb583b2399f67e43913d372` / `a874bd96360346aa9c706bf7fe8531cf82c6860c`。
- 负责人：Codex `/root`。
- 选择边界：把已完成隔离差分的 `mem_stage` replacement 接入活动 reachable overlay；不混入 IF/ID 或整机流水迁移。
- 锁定事实源：golden `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/mem_stage.v`；chiplab `a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`；myCPU gitlink `aa3bde1f3e720e71c2c78d6b81930d797b810149`；Vivado 2023.2 ML Standard build 4029153；Scala 2.13.16 / SpinalHDL 1.14.2 / Verilator 5.020。
- 行为合同：`docs/contracts/mem-stage.md`，49/49 legacy ports，保持 valid/flush、load/store、异常和 WB payload 周期语义。
- 修改文件：active replacement spec、status、reachability test，以及本目录日志和证据摘要。
- 失败尝试：WSL gitdir 下 Windows pytest 为 18 failed/14 errors，恢复 Windows 指针后为 323 passed/10 skipped；overlay 参数错误、dirty source、短 SHA 和误传 metadata 均被 fail-closed 拒绝；纠正后 clean committed overlay 成功。Claude job `6466a63ad05245ee9bd7bc059ff305c0` 因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败。
- Gate 结果：reachability 12/12 PASS；Scala 4/4 PASS；chiplab-doctor PASS；Vivado doctor PASS；Windows pytest 323/333（10 个既有平台 skip）；clean diagnostic overlay 接受 12 replacements；官方 smoke FAIL（功能 0/1，DUT warning 253，官方环境 warning 373）。
- 官方 smoke 证据：首个 mismatch 为 instruction `172552`、PC `0x1c07c79c`、`t0/r12` right `0x000006e2` vs wrong `0x00000008`，与锁定 baseline 首个失败点一致；这只支持“未观察到更早分歧”，不构成功能 PASS。
- 未执行：58/81、multi-seed random DiffTest、perf20、U-Boot/Linux、Vivado implementation/timing/bitstream、完整顺序形式等价。
- 独立审核：降级只读审核支持的最窄 claim 仅为“12 个 committed replacement 被 diagnostic overlay 接受，单一 func_lab19 未观察到比 baseline 更早的可见分歧”；不支持 integrated_pass 或功能通过。
- 残余风险：legacy Verilog backend 仍活动；253 个 DUT warning 未获逐条 waiver；Claude bridge 不可用；full regression 未执行。
- 回退：revert 本迭代提交即可移除 `mem_stage` active replacement 与状态计数。
- PR：`awaiting_pr`；提交并推送分支，不自动创建或合并。
- 下一候选：先保留 smoke 失败证据，随后独立 IF/ID active overlay，不与本分支混合。
