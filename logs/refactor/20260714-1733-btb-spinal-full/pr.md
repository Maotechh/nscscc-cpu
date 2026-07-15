# Draft PR：迁移完整 64-entry BTB 与 RAS predictor

- Iteration: `20260714-1733-btb-spinal-full`
- Branch: `refactor/20260714-1650-consolidated-spinal`
- Base / Head: `cc8e1f30fd27272849d65e0858873c5d2e15f1a3` / `eadf4415a94d890a09c382af215fd76f66ef1b54`
- 状态: Draft / `implementation_in_review`；不得自动创建、ready 或合并

## 行为变更

活动 Spinal backend 接入 64-entry 全相联 BTB、2-bit counter、16-entry return-site matcher 和 8-depth RAS。完整 PC 更新、delete、replacement 和 RAS 冲突策略是对 a158 设计意图的修正，不声明逐周期等价。

## 验证

predictor directed、26/26 ScalaTest、可复现生成、49-port contract、port-check、Yosys、replacement reachability 和 chiplab doctor 通过。mixed `func_lab19` 功能 parser 到 syscall 且无 mismatch，但 strict lint 与 smoke warning policy 失败；func-58/81、random、perf、system、Vivado 未执行。

## 回退与风险

回退 `508fe52` 和 `eadf441`。活动 fetch 接线尚缺完整功能与 random 证据，本 PR 不能进入 ready，也不能支持“CPU 已完全重构”的声明。完整详情见本迭代 `iteration.md` 与 `summary.json`。
