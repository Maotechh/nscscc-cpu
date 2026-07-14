# 独立只读 claim 审核

本审核是 Claude bridge 失败后的降级审查，不是 Claude 审核。

## Accepted

- `predictor-directed.json` 支持“隔离 predictor 定向合同 PASS”，不支持逐周期 golden 等价。
- Scala 4/4、26/26 证据来自 `508fe52`；`508fe52..eadf441` 没有 Scala/build 源变化，因此可以条件性归因给发布 HEAD。
- 两次生成 hash 稳定、49-port contract 和 Yosys 无 warning 支持生成可复现与静态端口/层次检查，不支持协议或时序正确。
- mixed `func_lab19` 的 174069 instructions、609803 clocks、到 syscall 和无 first mismatch 可作为诊断事实；必须同时保留 `gate_result=fail` 和 `gate_eligible=false`。
- Draft / `implementation_in_review` 是当前允许的最高状态。

## Fixed

- 最终 evidence、head、commands、artifacts 和 PR 草稿已同步到 `eadf441`，并将机器可读摘要随本提交纳入 Git。
- 原始 compile log 与 simulation trace 已记录路径、size、SHA256 和保留策略。

## Open / Blocking

- strict lint 和 smoke warning policy 失败，不能把 Yosys 或功能 parser 扩张为完整 rtl-static/smoke PASS。
- mixed overlay 不是 locked candidate，仍含旧 Verilog，不能证明纯 predictor 候选的官方行为。
- `good_trap=false` 且 UART 不适用；没有 func-58/81、random、perf、system 或 Vivado 证据。
- 端口 contract 不验证 AXI 握手、CDC、timing 或 Fmax。
- 大量 CPU 活动逻辑仍待完整 release 证据，不能声明完全重构。
