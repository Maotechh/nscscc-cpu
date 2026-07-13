# 20260713-2255-id-active-overlay

- 状态：draft；本地 source integration gate 已完成，等待以 clean commit 运行官方 overlay/smoke。
- 分支 / Base SHA：`refactor/20260713-2255-id-active-overlay` / `95da435a537703c091fa97bf6b4d352255207556`。
- 选择边界：把已完成四配置 ID leaf differential 的 `id_stage.v` 加入活动 replacement；不修改 MEM 分支、不混入 IF。
- Golden：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/id_stage.v`；replacement SHA `0a3c8434d828ad5d10f6c6431c0f811a8a476f67ed67160bcb5efa0c7cdfe516`。
- 已有 leaf 证据：normal/difftest/lacc/lacc-difftest 各 8259 cycles lockstep，完整 32x32 GPR diff，negative controls cycle 0，Scala/generation 2/2 reproducible。
- 尝试与失败：首次 Windows 自动化回归为 `1 failed, 322 passed, 10 skipped`，失败原因是 reachability 测试仍断言旧的 12 项计数；更新为 13 项并增加 `id_stage` module 断言后复测通过。10 项 skip 均为已有的非 Windows 平台测试，不计为 required gate PASS。
- 集成失败与修复：clean commit `636503abb67a4b913e459766b74638531800248b` 的首轮官方 smoke 在编译阶段严格失败，`mycpu_top.v:684` 报 `PINNOTFOUND rf_to_diff`，功能执行数为 0、skip 为 1，另有 32 条 DUT 和 103 条官方环境 warning。原因是 active metadata 明确锁定 `DIFFTEST_EN`，但 spec 误用了 normal-profile 生成物。修复为复现生成的 difftest-profile RTL（SHA256 `0148176ca9cbc477aa07363e5d0fcc897881a01da6481b66095c61a94331853b`），并增加 source-profile 回归断言；修复后必须重新形成 clean commit 和新 overlay，旧运行不得用于功能 claim。
- 修复验证：replacement reachability 重新 `13/13` PASS；difftest-profile ID 单元差分 `8192` cycles PASS；Windows 全量自动化回归 `323 passed, 10 platform skips`。normal-profile `id_stage.v` 保持原 SHA，不用 difftest 文件覆盖叶子合同。
- 已完成 gate：replacement reachability `13/13` PASS；Windows `pytest` 为 `323 passed, 10 platform skips`；Scala 四配置 `4/4` PASS（摘要 SHA256 `35676ee5ac04dcf24851f086c0c40c67d6816e364a35fbe5c2aa4fd0bd736322` 对应 evaluator）；锁定 chiplab doctor PASS（结果 SHA256 `70c193b0937ae42596c2bddb4d90542f4c2ff7ad712895777a504407042b34d3`）；Vivado 2023.2 doctor/hash PASS（结果 SHA256 `4c1d418d144f33e11d5b6af9179c5356c347686a1903eb355201c37c2ed0654f`）。
- 待完成 gate：修复后的 reachability/automation/ID difftest unit，随后以新 clean source commit 重建 diagnostic overlay 和官方 `func_lab19`，再完成 Claude 调用/降级独立审核、evidence-check、最终日志提交和 push。
- Claim 限制：不宣称 active integration、func PASS、58/81、random、perf、Linux、Vivado 或完整重构。
- Claude：必须调用并原样记录；缺 key 时降级为独立只读审核。
- 回退：revert 本迭代提交即可移除 ID replacement 与状态计数。
- 性能/资源：本迭代尚未运行 performance 或 Vivado implementation，不作任何周期、Fmax、LUT/FF/BRAM claim。
- 后续候选：IF active overlay（并行独立分支）或纯 Spinal active backend prerequisite；必须按实际依赖与证据重新选择。
- PR：`awaiting_pr`，代理不创建/不合并。
