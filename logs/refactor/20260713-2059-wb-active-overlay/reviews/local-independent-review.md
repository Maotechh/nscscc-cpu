# 独立只读审查

- 11 个 replacement 的 source blob、SHA256 和可达模块均由 locked overlay report 记录。
- 官方 build/simulation 的退出码为 0，但严格 warning policy 为 fail；这不是 RTL smoke PASS。
- 首个 DiffTest mismatch 与上一活动 overlay 同为 `0x1c07c79c`，只能说明未观察到更早的回归，不是顺序等价证明。
- WB 局部差分与 Scala gate 通过，但 IF/ID/MEM/BTB/perf、完整 CommitEvent 消费和 release FPGA gate 仍未完成。
