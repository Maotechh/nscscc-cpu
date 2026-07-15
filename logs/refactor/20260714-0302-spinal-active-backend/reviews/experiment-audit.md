# 实验完整性审计

- 日期：2026-07-14
- 审计对象：`2e5409a73841424540978e8dc43f6ba8b576a31e`
- 审计方式：按 `experiment-audit` 清单执行的独立只读降级审计
- 外部审计状态：Claude bridge 和 GPT-5.4 reviewer bridge 均不可用；本报告不得表述为跨模型审核
- 总体结论：`WARN`

## 检查结果

### A. Golden 来源：PASS

锁定 baseline 来自 `a158aa8` 和固定 chiplab `a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`，不是由 candidate 输出生成。来源和 trace 哈希记录在 `evidence/baseline-forwarding-comparison.json`。

### B. 指标处理：PASS

提交数、周期数、首个 mismatch、寄存器值和 next PC 均按原始 parser 输出报告，没有归一化成分数。末尾 30 行只替换时间戳后做相等性校验，且已明确限制为局部尾部证据，未外推为完整 trace 等价。

### C. 结果存在性：PASS

`rtl-smoke-2e5409a.json`、锁定 baseline summary、comparison 和 forwarding diagnosis 均存在；索引 SHA256 已复算匹配。candidate 为 172,548 条提交、603,892 clocks；baseline 为 172,552 条提交、602,903 clocks；两者均在 `0x1c07c79c` 首错。

### D. 执行链路：WARN

官方 smoke、Scala、生成、端口和 Yosys 均有实际命令结果。严格 lint 仍失败；58/81、random、perf、Linux 和 Vivado implementation/bitstream 未执行。历史 `commands.jsonl` 部分记录缺少实测 duration，不能补造。

### E. 范围：WARN

证据只支持本轮连续 store forwarding 回归消失，以及 candidate 到达 baseline 的已知首错。它不支持 `func_lab19` PASS、完整顺序 trace 等价、整机等价或完全重构完成。

### F. 评估类型：simulation_only / locked_reference_diff

本轮是锁定官方 chiplab/NEMU 仿真和锁定 Verilog baseline 对照；未执行 FPGA 板级、系统启动或完整测试集合。

## Claim 影响

- `C1`：`2e5409a` 修复 `0x1c0752b8` 连续 store 伪 forwarding 回归，`supported`。
- `C2`：candidate 到达 baseline 同一已知首错 `0x1c07c79c`，`supported_with_scope_limit`。
- `C3`：`func_lab19` PASS，`unsupported`。
- `C4`：完整顺序 trace/整机等价/完全重构完成，`unsupported`。

PR 必须保持 draft；严格 lint、官方 smoke、完整回归和外部 claim review 未闭合前不得提升状态。
