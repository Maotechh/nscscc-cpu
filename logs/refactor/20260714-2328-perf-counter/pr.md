# Draft PR：迁移并接入活动性能计数器

## 行为合同

七个 32 位计数器按 writeback event 独立计数；同步高有效 reset 优先；自然 2^32 回绕；事件可并发；不改变外部 core_top 端口。

## 验证

- Scala / unit differential / port-check / Yosys：PASS，证据见迭代目录。
- chiplab-doctor：PASS。
- 官方 `func_lab19` diagnostic mixed run：功能观察 PASS（syscall 终止、到达 test-end、无 mismatch）；严格 gate 因 warning policy 为 DUT 237、官方 364，且 provenance 非 gate-eligible 而 FAIL。
- 未运行或未通过：58/81 功能集、random、perf20、U-Boot/Linux、Vivado implementation/timing/bitstream。

## 审核与状态

Claude bridge 当前 unavailable（缺少 API key），不得把本地审查标为 Claude 审核。PR 保持 draft/awaiting_pr，由维护者审阅后决定是否创建和合并；代理不自动合并 `main`。

## 回退

revert 本迭代提交即可恢复旧 perf_counter backend 接线；保留 golden 和证据。
