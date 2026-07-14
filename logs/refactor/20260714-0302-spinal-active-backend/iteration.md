# 20260714-0302-spinal-active-backend

- Status: implementation_in_review
- Branch / Base SHA / Head SHA: `refactor/20260714-0302-spinal-active-backend` / `78efdf97b6208da3806fcbc02dca69061284d3b7` / pending
- Owner / Agent: Codex `/root`
- Selected boundary and selection reason: 活动整机 backend；它直接解除 `CoreTopCompat` 对 legacy Verilog BlackBox 的依赖，并把已经完成差分的 IF/ID/EX/MEM/WB、CSR、TLB、Cache 和 AXI 组件推进到同一个可生成的活动数据通路。
- Golden reference and locked tool versions: `a158aa8:rtl/`；详见 `reference/manifest.lock`，Vivado 固定为 2023.2。
- Behavior contract: 生成定义名保持 `core_top`，49 个官方端口不变；显式 `aclk/aresetn` ClockDomain；活动 backend 不得实例化 `openla500_legacy_core`；AXI/debug 必须由 typed Spinal 组件驱动。
- Files changed: 纳入 IF stage；新增 `SpinalCoreBackend`；兼容壳切换为纯 Spinal；新增 `CommitEvent`/实时 `ArchState` 到官方七个 DiffTest DPI 模块的条件适配；TLBFILL index 改由 CSR `rand_index` 提供；更新完整生成 package 与 replacement manifest。
- Attempts and failures: Windows scala gate 因 `/opt` 工具路径不可用失败；WSL 直接读取 Windows worktree 的 `.git` 路径失败，改用 WSL 原生验证 clone。首次 Scala gate 仅 scalafmt 失败，格式化后 4/4 通过。首次 port gate 因 `write_json` 前缺少 Yosys `proc` 失败，补回归后通过。`210f596` 官方 smoke 的 Verilator 构建成功，但仿真 600.054 秒超时，parser 观察到 0 条提交；FST 证明 IF/AXI/内部 `ws_valid` 活动，定位为生成 RTL 缺少官方 DiffTest DPI 实例。补齐适配后，严格 lint 仍因 88 条未批准 warning 失败，其中 31 条是 `DIFFTEST_EN` 关闭时壳输入未使用。
- Commands and gate results: 更新后 Scala 4/4、24 tests PASS；生成 2/2 可复现，wrapper SHA256 `1f9bec77f851848b5c2fd6ee327db11d424137fa0b64ed9fc2e00a93109b7aeb`；package SHA256 `748b025cedac922dbf6ff2707b61e6e230138b091c89ebe778b0eede446dea41`；publish/49-port/Yosys PASS；`DIFFTEST_EN` 加官方 `difftest.v` 的 Verilator 静态链接退出 0，但有既有 warning；Python 326 PASS、10 platform skip；严格 lint FAIL；新 adapter 的官方 smoke 待干净提交后执行。
- Functional/performance/resource delta: 尚未测量，不作声明。
- Residual risks: 新 DiffTest adapter 尚未通过官方 smoke；88 条 lint warning 未批准；adapter 单测是结构合同，尚无逐周期 DPI 仿真；debug breakpoint 下遵守“commit 不重不漏”不变量，不承诺复现 golden 重复 level 事件的历史缺陷；当前 predictor 仍为 32-entry direct-mapped 临时实现且不等价于 golden 可观察的 32 项全相联/RAS 行为；LACC、完整随机 DiffTest、perf 和 release gates 未完成；锁定 baseline 的 `func_lab19` 自身在 `0x1c07c79c` 失败。
- Rollback: revert 本迭代 PR；不影响 `main` 或既有参赛稳定分支。
- PR URL or awaiting state: awaiting_next_push；不自动创建或合并 PR。
- Next unblocked candidates: 使用新 adapter 重跑官方 smoke 并处理首个真实 DiffTest mismatch；随后迁移 golden 可观察的 BTB/RAS 行为；LACC 与性能计数器继续保持独立边界。
