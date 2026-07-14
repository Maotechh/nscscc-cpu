# 20260714-2328-perf-counter

- Status: `implementation_in_review`
- Branch / Base SHA / Head SHA: `refactor/20260714-1650-consolidated-spinal` / `5038a537a02c1778a13ceca6b07d26e311b9afd6` / `working-tree`
- Owner / Agent: Codex；独立只读子代理负责 golden 语义预审。
- Selected boundary and selection reason: `observe/perf_counter`。它是活动 `a158aa8` 顶层中最后一个已有 Scala 形状但尚未接入 `SpinalCoreBackend` 的显式状态模块；行为只有七个独立 32 位计数器，golden 可执行且 blast radius 小。
- Golden reference and locked tool versions: `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/perf_counter.v`；JDK 17.0.19、sbt 1.10.11、Scala 2.13.16、SpinalHDL 1.14.2、Verilator 5.020、Yosys 0.33。
- Behavior contract: `docs/contracts/perf-counter.md`；机器合同为 `reference/component-contracts/perf-counter.json`。
- Files changed: 待实现。
- Attempts and failures: 首次锁定 Scala gate 为 30/31 测试，通过格式/compile/test-compile，但新 directed test 越层读取子组件内部状态，触发 7 条 hierarchy violation；standalone 零输出 generator 另产生 14 条 pruned warning。第二次 gate 消除了 hierarchy violation，但 SimTop 的隐式 `clk/reset` 未消费，Verilator 以 2 条 `UNUSEDSIGNAL` 拒绝，standalone 仍有 14 条 pruned warning。第三次四项 sbt task 和 31/31 测试均通过，但 simulator policy 发现新 test 未显式启用 `CMPCONST/UNSIGNED`，因此总 gate 仍 fail。现已补齐完整 warning flags；未把任一失败记作 PASS。
- Commands and gate results: preflight PASS；contract、两次生成、port-check、observed lint、Yosys、8192 周期 lockstep 和 negative control 已 PASS；首次 unit compile 暴露 testbench 7 条 `WIDTHEXPAND`，正在修复后重跑。
- Functional/performance/resource delta: 本轮只迁移计数状态和接线，不做性能优化；未运行 Vivado，不声明 Fmax/LUT/FF/BRAM 变化。
- Residual risks: standalone 内部计数器没有架构输出；完整整机 warning、58/81、random、perf20、system、Vivado/FPGA 仍须独立证据。
- Rollback: revert 本轮提交即可恢复原 backend 未接线状态；不得删除锁定 golden。
- PR URL or awaiting state: `awaiting_pr`；只推送分支，不自动创建 ready PR 或合并。
- Next unblocked candidates: 整机 strict warning 归因与清理、完整官方 gate wrapper 和锁定 Vivado 验证。

## 预检

- `git status --short --branch`：工作树干净，分支与远端同名分支同步。
- `git rev-parse HEAD`：`5038a537a02c1778a13ceca6b07d26e311b9afd6`。
- `git rev-parse --verify origin/main`：`20cae5fd66391f4a1bccc1b87035be421039144b`。
- 远端：`origin=https://github.com/Maotechh/nscscc-cpu.git`。
- 本轮继续使用唯一长期重构分支，不创建新的功能 worktree/分支；这是用户明确要求的串行提交策略，仍不触碰 `main`。

## Golden 初步结论

- 九个端口：`clk/reset` 加七个单 bit 事件输入，无输出端口。
- 七个 32 位寄存器在时钟上升沿独立自增；同周期多个事件可同时计数。
- `reset` 为同步高有效，优先于全部事件；自然模 2^32 回绕。
- golden 顶层由 `wb_stage` 的 `real_*` 事件驱动，计数器没有被官方 testbench 作为架构状态读取。
