# PR 草案：隔离退休状态更新关键路径

## 摘要

将 ROB 三路退休产生的 FreeList 释放和分支预测器训练各延迟一拍，补齐恢复周期的
FreeList/RAS 合并语义，减少完整 SoC 中 ROB 到远端多写口状态的高扇出组合路径。

## 已验证

- Scala/Spinal/Verilator 130/130
- Python 362/362
- lint、端口、Yosys、发布一致性全部通过
- 自动生成 RTL：`0ec54fa65e5179a78d82845fc6e722e768dc3637eb8d426c1aad1a4d64d854a6`
- Vivado 2023.2 独立综合：100 MHz WNS `+0.359 ns`

## 待验证

- 完整 SoC 100 MHz implementation、DRC 与 WNS
- 三次真实 perf20 的 20/20 功能结果和最低执行时间

