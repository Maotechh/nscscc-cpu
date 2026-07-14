# 20260714-1733-btb-spinal-full

- Status: `draft`
- Branch / Base SHA / Head SHA: `refactor/20260714-1650-consolidated-spinal` / `cc8e1f30fd27272849d65e0858873c5d2e15f1a3` / 待实现
- Owner / Agent: Codex；独立只读 predictor 合同审核子代理
- Selected boundary and selection reason: `predictor/full_btb_ras`。它是活动 backend 最大的明确临时实现，直接解除 `CoreConfig` 64/16 配置与实际 32-entry always-taken 逻辑的冲突。
- Golden reference and locked tool versions: `a158aa8:rtl/btb.v` 的名义 64-entry/2-bit/RAS 行为，加已验证 BTB replay 修复；工具使用 `reference/manifest.lock`。
- Behavior contract: `docs/contracts/predictor.md`
- Files changed: 待填写。
- Attempts and failures: 待记录。
- Commands and gate results: 待执行。
- Functional/performance/resource delta: 本轮不做性能优化；资源变化待 Vivado/综合证据。
- Residual risks: a158 本身有 32/64 位宽缺陷，不能用其逐位 RTL 作为完整 truth；正式 func/random/fpga wrapper 仍缺失。
- Rollback: revert 本迭代 predictor 实现、接线和发布提交；保留 `cc8e1f3` 单一集成基线。
- PR URL or awaiting state: `awaiting_pr`；不得自动创建或合并。
- Next unblocked candidates: LACC 活动集成；统一 runtime overlay；补 func/random/perf/fpga wrapper。
