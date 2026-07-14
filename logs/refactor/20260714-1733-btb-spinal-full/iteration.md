# 20260714-1733-btb-spinal-full

- Status: `draft`
- Branch / Base SHA / Head SHA: `refactor/20260714-1650-consolidated-spinal` / `cc8e1f30fd27272849d65e0858873c5d2e15f1a3` / 本提交后补
- Owner / Agent: Codex；独立只读 predictor 合同审核子代理
- Selected boundary and selection reason: `predictor/full_btb_ras`。它是活动 backend 最大的明确临时实现，直接解除 `CoreConfig` 64/16 配置与实际 32-entry always-taken 逻辑的冲突。
- Golden reference and locked tool versions: `a158aa8:rtl/btb.v` 的名义 64-entry/2-bit/RAS 行为，加已验证 BTB replay 修复；工具使用 `reference/manifest.lock`。
- Behavior contract: `docs/contracts/predictor.md`
- Files changed: 新增独立 `OpenLa500Predictor` 和定向 ScalaTest；`SpinalCoreBackend` 接入 typed lookup/update Flow；`CoreConfig` 分离 16 项 return-site matcher 与 8 深 return stack；修订行为合同与证据日志。
- Attempts and failures: 首次 SBT 命令的 `Test / testOnly` 参数格式错误，未执行测试；首次 predictor 仿真因 5 个 `UNUSEDSIGNAL` 告警被 `-Wall` 拒绝；第二次仿真在 testbench 二次拉高隐式 reset 后停在 Verilator eval，调用 184 秒超时，孤立进程经 `jstack` 定位后约 624 秒显式终止。随后改为完整地址存储消除未使用位，并采用一次上电 reset、公开 update 清理状态，未放宽 warning policy。
- Commands and gate results: 锁定 JDK 17.0.19、SpinalHDL 1.14.2、Verilator 5.020 下 predictor 定向测试 1/1 PASS；pre-commit 隔离副本 `make scala-check` 4/4 task、26/26 ScalaTest PASS，主/测试源码 56/16，skipped=0。机器证据见 `evidence/predictor-directed.json` 与 `evidence/scala-precommit.json`。
- Functional/performance/resource delta: 本轮不做性能优化；资源变化待 Vivado/综合证据。
- Residual risks: a158 本身有 32/64 位宽缺陷，不能用其逐位 RTL 作为完整 truth；当前实现有完整 PC 重匹配、delete 生效、64 项可访问、当前拍 strongly-untaken 和 RAS 冲突优先等意图修正，不声明逐周期等价。活动 fetch 接线属于流水控制影响，但仓库尚无 `rtl-func-58/81` 与 `rtl-random` 入口，因此本迭代只能保持 Draft。
- Rollback: revert 本迭代 predictor 实现、接线和发布提交；保留 `cc8e1f3` 单一集成基线。
- PR URL or awaiting state: `awaiting_pr`；不得自动创建或合并。
- Next unblocked candidates: LACC 活动集成；统一 runtime overlay；补 func/random/perf/fpga wrapper。
