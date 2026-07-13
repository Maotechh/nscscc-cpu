# 实验完整性审计

总体结论：`WARN`。当前环境没有 experiment-audit 所要求的独立 GPT-5.4 MCP，因此由独立只读子代理降级审核，不能表述为跨模型审计通过。

- 官方 chiplab/NEMU 与锁定 baseline 都有明确 provenance；没有自生成 ground truth 或自归一化分数。
- compact evidence 中的数字、SHA256、大小均与源报告核对。
- 实际范围只有一个失败的 `func_lab19`；58/81、随机、性能、系统和 FPGA gate 未执行。
- 允许两个有限 claim：diagnostic overlay 接受 13 个 committed replacement；该单一失败 trace 与 baseline 字节一致且未观察到更早可见差异。
- 不支持功能通过、顺序等价、integrated pass 或完全重构。
