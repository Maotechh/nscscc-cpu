# 20260713-2059-wb-active-overlay

- Status: draft（官方严格 smoke 失败，未创建 PR）
- Branch / Base SHA / Head SHA: `refactor/20260713-2059-wb-active-overlay` / `288c4c834244b4b3e6ee03198124a82774d52002` / `464ccd3d200aa281749322229e913c3ef275bcc5`
- Owner / Agent: Codex / root
- Selected boundary and selection reason: 将已通过局部合同的 WB replacement 接入活动 legacy shell，验证组合后的可达性、官方层级构建和首个 DiffTest 位置。
- Golden reference and locked tool versions: chiplab `a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`、myCPU gitlink `aa3bde1f3e720e71c2c78d6b81930d797b810149`、golden candidate `a158aa8`、Vivado 2023.2 ML Standard、Verilator 5.020、JDK 17。
- Behavior contract: 11 个 committed replacement 在 `legacy_lacc_off_difftest_on` 下由 `core_top` 可达；WB 保留普通/DIFFTEST 端口、断点锁存和单次 CommitEvent。
- Files changed: active replacement spec/meta、WB replacement/gate/source（来自前置迭代）、reachability regression assertion、集成日志和状态。
- Attempts and failures: 初次全仓测试发现 reachability 数量仍硬编码 10，更新为 11 并重新通过；严格官方 smoke 原生 build/simulation exit 0，但 warning policy 失败（DUT 254、官方 373），DiffTest 仍在 baseline 同点 `0x1c07c79c`。
- Commands and gate results: reachability 11/11 PASS；Scala 4/4 PASS；全仓 318 PASS、10 个已知 skip；chiplab doctor PASS；Vivado 2023.2 batch probe PASS；overlay loader 接受 11 blobs（diagnostic）；official func smoke FAIL。
- Functional/performance/resource delta: 仅 legacy shell 组合验证；没有 58/81、random NEMU、perf20、U-Boot/Linux、Vivado synth/implementation/timing/bitstream 证据。
- Residual risks: Scala 仍非活动 CPU 唯一手写真源；IF/ID/MEM/BTB/perf/AXI 整体行为未迁移；warning policy 与 baseline mismatch 阻塞 release；Claude bridge 缺少 `GEEKPIE_CLAUDE_API_KEY`。
- Rollback: revert integration commit and retain prior `refactor/20260713-1847-active-overlay` branch; no main merge performed。
- PR URL or awaiting state: `awaiting_pr`；分支尚未推送，待日志提交后 push；代理不创建或合并 PR。
- Next unblocked candidates: 先定位 WB 组合后 warning 增量并建立 warning baseline，再迁移 MEM/IF/ID；所有整机 claim 继续保持 draft。
