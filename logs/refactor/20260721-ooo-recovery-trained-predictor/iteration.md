# ROB 恢复训练的 32-entry 方向/目标表

日期：2026-07-21

## 选择依据

上一提交的 B/BL + BTFNT 已消除大部分直接跳转和循环后向分支恢复，但 JIRL、前向 taken 和反静态方向仍必然在第一次执行时恢复。参考 `ysyx-workbench` `la32r-linux` 分支的 banked BTB、PHT 和 RAS 后，本轮没有直接迁移完整 speculative GHR/RAS，而是先建立最窄的精确反馈通道。

## 设计

* `OooRecoveryRequest` 增加内部 `pc` 和实际 `taken`，ROB 从已完成 entry 在有序恢复边界产生数据；公开 `core_top` 和 505-bit `CommitEvent` 不变。
* ROB entry 和 accepted-completion stage 保存实际 branch taken，避免从目标地址反推方向。
* 前端增加 32-entry direct-mapped 表，每项保存 valid、25-bit PC tag、方向和 32-bit 目标。
* 只有已到 ROB head 的 branch mispredict 更新表；正确预测和被 squash 的 speculative branch 不更新。
* 动态命中覆盖 BTFNT 冷启动结果，可学习前向 taken、后向 not-taken 和 JIRL 最近目标。
* 预测方向/目标随 instruction-buffer slot 保存，decode 不重新查询可变表。

该结构不是 ysyx 的 128-entry banked BTB + 1024-entry gshare PHT + 8-entry speculative/architectural RAS；后者仍是后续可独立验证的升级方向。

## 结果

固定 `func/func_lab19`、NEMU DiffTest、bus delay seed `5570815`：

| 配置 | Instructions | Clocks | IPC |
| --- | ---: | ---: | ---: |
| 上一提交静态预测 | 131,198 | 744,827 | 0.176146 |
| 32-entry 恢复训练 | 131,226 | 743,893 | 0.176404 |

减少 934 周期（0.125%）。两次都到达 end PC 并以 `END by Syscall` 结束；候选无 DiffTest mismatch。

## 验证与综合

最终生成 RTL SHA-256：
`270152e4dd38aa9c1598b232b2e115eea5245088fa417f41c9b9b74fb444aba3`。

| 检查 | 结果 |
| --- | --- |
| Scala/Spinal/Verilator | 35 suites，85/85 passed；前端含反 BTFNT 学习定向测试 |
| Python repository tests | 362/362 passed |
| package、port、lint、Yosys、publish | 全部通过；lint 665 条精确签名 |
| Chiplab `func_lab19` | 通过；743,893 clocks，IPC 0.176404 |
| Vivado 2023.2 | 0 synthesis errors；WNS +0.419 ns，TNS 0，0 failing endpoints |
| 资源 | 71,687 LUT，39,563 FF，42 RAMB36，12 RAMB18，4 DSP |

相对上一提交增加 913 LUT 和 2,275 FF，时序不退化。器件容量仍足够，但单位资源收益较低；下一轮不应继续扩大同类寄存器表，优先评估 banked RAM 或减少恢复总延迟。

## 合规与限制

全部 CPU 修改是 Scala/SpinalHDL；生成 RTL 保持忽略且由锁定流程重建。没有手写 Verilog、软件地址识别、DiffTest 跳过或时序例外。远程 FPGA skill 不可用，未获得三次烧录结果，因此只声明固定官方仿真的周期变化。
