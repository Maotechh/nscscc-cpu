# 退休状态更新时序隔离

日期：2026-07-27

## 本轮目标

完整 SoC 在提交 `eec818de9a094495a5dd38dfd35b16c9b0c5fcb0` 上以 100 MHz
实现后的 WNS 为 `-0.515509 ns`、TNS 为 `-102.434494 ns`，共有 748 个失败端点。
最差路径从 ROB 三路提交判定出发，终止于 FreeList；前 100 条最差路径中，36 条终止于
FreeList，64 条终止于分支预测器的体系结构 RAS。因此本轮不改变 4 发射、5 回写、3 提交
和 64 B L1/L2 cache line 的体系结构，而是在退休边界插入寄存器，切断 ROB 提交前缀到
远端多写口状态的组合路径。

## 修改内容

- 在 `OooBackend` 中寄存三路已退休物理寄存器释放请求，使 FreeList 不再由当拍 ROB
  提交前缀直接驱动。
- FreeList 在恢复周期仍接收上一拍已经成为体系结构状态的释放批次，并以更新后的
  `architecturalHeadPtr` 和 `architecturalFreeCount` 恢复推测状态，避免回滚到过期快照。
- 在 `OooCore` 中寄存分支预测器退休训练信息，切断 ROB 到 BTB/PHT/RAS 写网络的路径。
- 当上一拍退休训练与本拍恢复同时发生时，`OooBankedFetchPredictor` 将 RAS push/pop
  合并进恢复后的推测 RAS；既有 GHR 合并语义保持不变。
- 新增 FreeList “延迟释放与 flush 同拍”测试以及预测器 “RAS push 与 flush 同拍”测试。

## 时序语义

ROB 在周期 N 给出退休和 recovery，`OooCore` 在周期 N+1 才产生内部 redirect/flush。
本轮寄存的 FreeList 释放与预测器训练也在 N+1 生效，所以它们必须在 flush 周期保留，
而不是被 flush 丢弃。外部 redirect 和已经存在的内部 redirect 会阻止捕获新的退休批次。

## 本地门禁

| 检查 | 结果 |
| --- | --- |
| 定向 Scala/Verilator | 2 suites，8/8 passed |
| `scalafmtCheckAll` | passed |
| 全量 Scala/Spinal/Verilator | 36 suites，130/130 passed，约 3 分 09 秒 |
| Python repository gates | 362/362 passed，约 31.7 秒 |
| generated-top lint | 853 条已锁定 `CMPCONST`/`UNUSEDSIGNAL`，签名未变 |
| port/Yosys/publish | 全部通过；官方 49-port 合同和发布来源一致 |
| generated RTL SHA-256 | `0ec54fa65e5179a78d82845fc6e722e768dc3637eb8d426c1aad1a4d64d854a6` |
| standalone Vivado 2023.2 | `xc7a200tfbg676-2`，100 MHz，0 synthesis error，WNS `+0.359 ns` |

独立综合没有加载板级 SoC、IP 和完整 XDC，因此其 WNS 不是完整实现的时序闭合证据；
顶层未约束端口引起的 `NSTD-1`/`UCIO-1` 也不用于判断完整 SoC DRC。

## 规则审核

CPU 功能只修改 Scala/SpinalHDL 源码；`rtl/mycpu_top.v` 由锁定生成流程自动生成并由
replacement/publish 哈希绑定。本轮不读取测试程序身份、答案或未声明外部状态，不引入
手写 CPU Verilog，也不修改比赛参考、器件、Vivado 版本或目标时钟约束。

## 下一门禁

推送完整 40 位候选提交后，使用锁定 chiplab 和 Vivado 2023.2 构建
`perf20@100MHz` 完整 SoC。先检查 implementation 完整性、DRC 和 WNS；只有 WNS
非负才能声明 100 MHz 时序闭合。若闭合，再执行三次真实 perf20，并以三次完整通过结果
中的最低程序执行时间相对基线 `2.06902887 s` 判定性能。

