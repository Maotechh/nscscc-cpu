# LACC 独立只读审核

- 审核者：`/root/lacc_dcache_harness` 独立只读代理
- 审核对象：基于 `2d09948802ed9bef9e63afd92061173ba5a3714b` 的未提交 LACC 实现快照、完整 diff、行为合同、门禁摘要和原始本地 artifact
- 总体结论：`WARN / draft-only`
- 状态上限：LACC 叶子可维持 `differential_pass`；整轮保持 `draft`，不得提升为 `integrated_pass`、ready PR、整机静态通过或完全重构

## 阻塞问题

1. 审核时源码尚未锚定提交，`summary.json` 的 base/head 都是 `2d09948`。提交后必须重跑 source-sensitive gates，才能声称提交 HEAD 通过。
2. required `rtl_static` 明确失败：LACC-off/on 分别有 80/81 条 whole-top strict Verilator warning；Yosys PASS 不能替代该失败。
3. 官方 smoke 尚未在本轮提交上执行，因此 build/generator/top 变更只允许 draft。
4. `ExecuteStage` 当前把 LACC flush 固定为 `False`。这与 a158 `exe_stage.v` 中未驱动的兼容输出相符，可解释 two-state 差分，但尚未形成 top 级异常/flush 安全合同，不能外推为四态或综合等价。

## Claim disposition

- `lacc_two_state_cycle_diff`：`qualified`。仅支持 Verilator 5.020 two-state、锁定 seed `0x158aa8`、8192 周期、合法有序 response 下的可观察 valid/payload/memory/backpressure 逐周期一致；不支持四态、形式、多 seed 或整机等价。
- `lacc_dcache_directed`：`qualified`。仅支持 typed LACC+DCache 的一个跨 line miss/refill 定向场景；未覆盖 Execute、地址转换、AXI 或官方 workload。
- `dual_config_elaboration_yosys`：`accepted`。LACC-off/on 均可复现 elaboration 和 canonical package，并通过 Yosys hierarchy/check；必须同时披露 strict lint FAIL。
- `standalone_candidate_lint_clean`：`accepted`。只指独立 LACC candidate 0 warning，不得表述为 whole-top lint PASS。
- `active_integration_complete`、官方功能、random DiffTest、Vivado/FPGA、release-ready、完全重构：`rejected`。
- `claude_review_completed`：`rejected`。Claude job 在执行前因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败，本轮仅完成独立只读代理审核。

## 非阻塞建议

- 后续为 response payload/address/write-data 增加逐项 fault injection；当前 negative control 只证明 comparator 能捕获 response-valid 故障。
- 评估删除或解释未消费的 `ExecuteLaccInput.requestReady`，它是 LACC-on 相比 off 唯一新增的 whole-top warning。
- LACC+DCache harness 不包含 ExecuteStage、AddrTrans 或 AXI，不得把该定向测试写成真实 whole-top 集成完成。
