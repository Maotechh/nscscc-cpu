# 实验完整性审计

## 结论：WARN

未发现 phantom result、用 candidate 反向生成 golden、self-normalization 或隐藏 skip。最终本地摘要均存在，关键结果绑定 `9e78538c0dec08fa9fcace49e068b8bc9d4d5af1`、锁定 RTL 哈希、driver 和 vectors。

按 `experiment-audit` skill 计划使用独立 GPT-5.4 reviewer，但本会话没有 `mcp__codex__codex`；Claude bridge 又在模型启动前缺少 `GEEKPIE_CLAUDE_API_KEY`。因此外部跨模型审计状态是 `unavailable`，不能表述为已完成外部审核。降级为独立只读代理核对原始文件、数字和 claim。

## 核对结果

- Golden 来源是锁定的 `a158aa8:rtl/div.v`，不是 candidate 输出。
- Candidate 差分实际为一次 runner 中的 40 directed + 4096 fixed-seed random transaction；不是 4136 次独立 run，也不是穷举。
- Formal 只证明 reset 后 2-state 协议时序；算术和 golden 顺序等价明确为 false。
- Chiplab 两侧均执行且均失败，`identity-comparison.json` 也是 fail；只允许报告单个已知失败 case 的选定观测一致。
- Vivado 只完成 standalone leaf synthesis。两侧 timing 未收敛且 DRC/methodology 有未解决项，不能报告 timing/Fmax/FPGA PASS。
- 58/81、multi-seed、perf、U-Boot、Linux、implementation、bitstream 和板卡均未执行。

机器可读逐项核对见 `evidence/claim-audit.json`。
