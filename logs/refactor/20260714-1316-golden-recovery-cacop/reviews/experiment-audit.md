# 实验完整性审计

本审计由独立只读子代理完成，不是 GPT-5.4/Codex MCP 审核；当前环境没有该 MCP，不能冒充 cross-model 结果。

## 结论：FAIL

这里的 FAIL 指证据计数和可追溯性需要修正，不是重复声明功能实现失败。审计提出的问题已按下列方式处理，但迭代仍保持 blocked：

1. 历史二分四次顶层 strict smoke 均失败，d22 只通过 functional parser。`history_bisect` 已从 4 PASS 改为 0 PASS / 4 FAIL。
2. 最终 lint JSON 只能复核 `status=fail`，不能复核精确 warning 数量。日志和 PR 已删除数量声明。
3. CACOP 定向 JSON 能绑定两个候选 RTL SHA、958/4790 拍、零 mismatch 和负控，但没有 source HEAD、evaluator SHA、Verilator 版本或原始 trace locator。C1 已限定为仅对 `0e0a...932c` / `ebf5...392a` 两个 RTL 哈希成立，不能直接绑定为 `b2a73c8` 整机证据。
4. official smoke 是 `gate_eligible=false` 的 mixed diagnostic overlay。它只证明执行 1 次并在 NEMU `0x1c07cfcc` / DUT `0x1c07cfdc` 失败，不能称 locked candidate 或 official gate PASS。

Oracle blob 固定、无自归一化、定向数字算术和负控检查均通过审计。58/81、random、perf20、U-Boot、Linux、Vivado release 和完全重构仍无证据。
