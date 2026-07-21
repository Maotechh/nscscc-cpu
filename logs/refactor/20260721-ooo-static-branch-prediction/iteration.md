# 静态直接跳转与 BTFNT 预测

日期：2026-07-21

## 目标

在不增加预测表和恢复协议复杂度的前提下，减少当前 OoO 前端对直接跳转和循环后向分支的必然恢复开销，并重新建立可信的官方仿真基线。

## 设计

`OooFrontend` 在 I-cache 返回四条指令时做静态预解码：

* `B`、`BL` 总是预测 taken，目标由 26-bit 立即数直接计算；
* 条件分支采用 backward-taken/forward-not-taken；
* `JIRL` 保持 not-taken，因为目标依赖寄存器；
* 一个 16B 响应组只保留第一条预测 taken 分支及其之前的指令，下一取指 PC 直接改为目标；
* decode 侧重新计算同样的 `predictedTaken/predictedTarget`，已有 completion recovery 继续处理错误预测。

官方仿真重新编译时发现旧结果曾复用早于 RTL 的 Verilator archive。强制重新编译后还暴露出 1483ef0 对特权副作用分级时遗漏了 TLBFILL 随机索引：有效脉冲延迟一拍，但 `timer64(4:0)` 索引没有随 payload 捕获。当前实现增加 `committedTlbRandomIndex`，使硬件 TLB 写入索引与提交事件/NEMU 一致。

CSR/TLB/ERTN 状态比普通 GPR 提交晚一拍生效。`ChiplabMultiCommitDiffTestAdapter` 因此使用固定三拍事件观察流水：普通架构状态使用提交后一拍的快照，串行事件使用已落地的实时 CSR 状态。固定延迟不会覆盖或重排后续提交批次，且保持既有 505-bit `CommitEvent` 合同不变。

## 性能

两组仿真都使用 `func/func_lab19`、NEMU DiffTest、bus delay seed `5570815`，并显式依次执行 `make verilator`、`make testbench` 和 `simulation_run_prog`。

| 配置 | Instructions | Clocks | IPC |
| --- | ---: | ---: | ---: |
| 公平基线：关闭静态预测 | 126,157 | 783,358 | 0.161046 |
| 候选：B/BL + BTFNT | 131,198 | 744,827 | 0.176146 |

候选减少 38,531 周期，即 4.92%。两次都通过 DiffTest，以 `END by Syscall` 结束并到达 end PC。指令数不同来自测试软件控制流路径变化，因此性能比较以相同工作负载的总结束周期为准。

旧的 126,136 instructions / 776,232 clocks 记录没有重新生成 `obj_dir/Vsimu_top__ALL.a`，不能作为性能基线。

## 验证

最终生成 RTL SHA-256：
`3b41c55bb6fa52895da85728a259e43aa42f335aa5718978402e6dbe251ef7b2`。

| 检查 | 结果 |
| --- | --- |
| Scala/Spinal/Verilator | 35 suites，85/85 passed |
| Python repository tests | 362/362 passed |
| package、port、lint、Yosys、publish | 全部通过；lint 精确锁定 665 条已审计项 |
| Chiplab `func_lab19` + NEMU | 通过；744,827 clocks，IPC 0.176146 |
| Vivado 2023.2 | 0 synthesis errors；WNS +0.419 ns，TNS 0，0 failing endpoints |
| 资源 | 70,774 LUT，37,288 FF，42 RAMB36，12 RAMB18，4 DSP |

Standalone DRC 的 NSTD-1/UCIO-1 来自没有板级 XDC；其余是配置电压和 DSP pipeline 建议。没有使用 false path 或降低时钟要求。

## 合规与限制

CPU RTL 改动全部位于 Scala/SpinalHDL 源码；`mycpu_top.v` 由锁定生成流程产生且保持 Git ignore。没有手写 Verilog、仿真跳过、软件识别或结果硬编码。远程 FPGA 评测 skill 当前不可用，因此没有真实烧录数据，本轮只声明官方仿真周期改进和 standalone 综合结果。
