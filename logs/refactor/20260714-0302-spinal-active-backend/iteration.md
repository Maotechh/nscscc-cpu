# 20260714-0302-spinal-active-backend

- Status: implementation_in_review
- Branch / Base SHA / Head SHA: `refactor/20260714-0302-spinal-active-backend` / `78efdf97b6208da3806fcbc02dca69061284d3b7` / pending
- Owner / Agent: Codex `/root`
- Selected boundary and selection reason: 活动整机 backend；它直接解除 `CoreTopCompat` 对 legacy Verilog BlackBox 的依赖，并把已经完成差分的 IF/ID/EX/MEM/WB、CSR、TLB、Cache 和 AXI 组件推进到同一个可生成的活动数据通路。
- Golden reference and locked tool versions: `a158aa8:rtl/`；详见 `reference/manifest.lock`，Vivado 固定为 2023.2。
- Behavior contract: 生成定义名保持 `core_top`，49 个官方端口不变；显式 `aclk/aresetn` ClockDomain；活动 backend 不得实例化 `openla500_legacy_core`；AXI/debug 必须由 typed Spinal 组件驱动。
- Files changed: 纳入 IF stage；新增 `SpinalCoreBackend`；兼容壳切换为纯 Spinal；完整生成 package；纯整机 gate 和单文件 overlay 合同。
- Attempts and failures: Windows scala gate 因 `/opt` 工具路径不可用失败；WSL 直接读取 Windows worktree 的 `.git` 路径失败，改用 WSL 原生只读验证 clone。首次 Scala gate 仅 scalafmt 失败，格式化后 4/4 通过。首次 port gate 因 `write_json` 前缺少 Yosys `proc` 失败，补回归后通过。严格 lint 因 87 条未批准 warning 失败。
- Commands and gate results: Scala 4/4 PASS；生成 2/2 可复现；package/publish/49-port/Yosys/reachability PASS；Python 326 PASS、10 platform skip；lint FAIL；官方 smoke 尚未执行。
- Functional/performance/resource delta: 尚未测量，不作声明。
- Residual risks: 整机功能尚未通过官方 smoke；87 条 lint warning 未批准；当前 predictor 仍为 32-entry 临时实现；LACC、完整 DiffTest/ArchState、perf 和 release gates 未完成；锁定 baseline 的 `func_lab19` 自身在 `0x1c07c79c` 失败。
- Rollback: revert 本迭代 PR；不影响 `main` 或既有参赛稳定分支。
- PR URL or awaiting state: awaiting_push；不自动创建或合并 PR。
- Next unblocked candidates: 完整 DiffTest/ArchState adapter、64-entry BTB 活动接入、LACC、性能计数器。
