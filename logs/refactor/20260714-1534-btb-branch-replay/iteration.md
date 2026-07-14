# 20260714-1534-btb-branch-replay

- Status: `draft`
- Branch / Base SHA: `refactor/20260714-1534-btb-branch-replay` / `372eccc9b54fb5a80f08bc5af6dcc8944ea3e8fa`
- Owner / Agent: Codex；独立子代理只读定位 BTB replay
- Selected boundary and selection reason: `predictor/branch_replay`。上一迭代 official diagnostic smoke 的新首错是第二轮 `0x1c07cfdc` 重复提交；只读审查将高置信根因定位到 lookup PC 未绑定 `fetchEnable`，该边界 blast radius 小且可用现有 smoke 验证。
- Golden reference and locked tools: d22/a158 `rtl/btb.v` 的 fetch_en_r/fetch_pc_r 语义；chiplab `a2e11b3`；Scala 2.13.16；SpinalHDL 1.14.2；Verilator 5.020；Vivado 2023.2。
- Behavior contract: `docs/contracts/btb-branch-replay.md`
- Rollback: revert 本迭代 PR；保留上一迭代 CACOP 分支为基线；不修改或合并 `main`。
- PR: `awaiting_pr`，不得自动创建、标记 ready 或合并。

## 初始诊断

- `SpinalCoreBackend.scala` 当前使用 32-entry direct-mapped、always-taken 临时 predictor，不是 CoreConfig 声明的 golden 64-entry/2-bit/RAS BTB。
- 现有 `btbLookupPc = RegNext(fetch.io.fetchPc)` 每拍无条件更新，`lookupHit` 没有延迟 `fetchEnable` 有效位。
- d22/a158 只在 `fetch_en` 时锁存 PC，并用 `fetch_en_r` 限制 lookup。重复 `cfdc` 与首次 BTB 命中同周期出现，尚未由 harness 证明。

## 当前尝试

尚未修改 RTL；先建立合同、分支日志和最小回归，再实现一行行为修复并执行 change-impact gate。
