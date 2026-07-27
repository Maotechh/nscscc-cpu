# Main TLB walk result register

日期：2026-07-27

## 目标与起点

本轮从提交 `47f1573e3d2e230109319a88eb08d5b5adf4a78c` 开始。该提交把 L2/L1D
写回、refill 输出和前端纠错 kill 从组合反馈中拆开，但锁定的 100 MHz 完整 SoC
implementation 仍为 WNS/TNS `-0.374067/-13.675565 ns`，最差路径来自主 TLB
entry bank 到 `exception_badVAddrValid`，数据延迟 `10.050 ns`，其中 `7.839 ns`
（78%）为布线，179 个 setup failing endpoints。

对照上一级 `ysyx-workbench` 的 `MainTLB.scala`，其主 TLB 查找明确分为 `sWalk` 和
`sEnd`，并用 `tlbSliceHitReg`/`tlbSliceHitEntryReg` 先寄存查找结果，再生成翻译响应。
本实现之前在 walk 完成拍直接把组合 `walkMatch/walkEntry` 送入异常和地址转换响应，
因此保留了相同的主 TLB -> exception 组合长路径。

## 保留的实现

- 主 TLB walk 完成时只捕获 owner、命中、entry、index、VPPN 和 odd-page 到结果寄存器；
  下一拍才清除对应 walk pending、填充 micro-TLB/negative entry，并发出翻译响应。
- `startWalk` 在 `walkResponsePending` 期间禁止重新启动同一请求，避免结果响应拍把
  尚未清除的 pending 再次变成新的 walk。
- micro-TLB hit 仍保持原一拍响应；只有 micro-TLB miss 的主表扫描增加一拍，和 ysyx
  的 `sWalk -> sEnd` 边界一致。TLB mutation 会同步清空活动 walk 和待处理结果。
- 测试中的主表 miss 期望延迟从至少 9 拍更新为至少 10 拍；micro-TLB hit 的精确一拍
  行为保持不变。

## 本地功能与生成门禁

| 检查 | 结果 |
| --- | --- |
| TLB 定向测试 | 2/2 passed；主表 miss 延迟断言更新为 `>=10`，micro-TLB hit 仍为 1 拍 |
| Scala/Spinal/Verilator 全量 | 36 suites，130/130 passed |
| Python repository gates | 362/362 passed |
| package/port/Yosys/publish | 全部通过，49-port、`TLBNUM=32` 合同不变 |
| exact generated-top lint | 853 条，仅 `CMPCONST`/`UNUSEDSIGNAL`，精确 closure 通过 |
| lint signature | `5c7dc1c4b5d8261b216d5a2222fef205d17d133ad9175ad18efc188e3985e836`，未新增 warning |
| generated RTL SHA-256 | `924d9cad749c5d5ace575fa9d6534ca642b0c5105672e1b262f40ad8bcc34fd2` |

官方 Chiplab `func/func_lab19` 在删除旧 `obj_dir/output`、重新执行 Verilator、testbench
和软件编译后通过 NEMU DiffTest，以 `END by Syscall` 结束并到达 end PC：139,668
instructions / 552,247 clocks / IPC 0.252909。与上一提交的同一 workload、seed
`5570815` 和已重新编译 RTL 的结果完全相同。

## Standalone Vivado 证据

Vivado 2023.2、`xc7a200tfbg676-2`、10 ns 时钟、`general.maxThreads=8` 综合结果：

- WNS `+0.419 ns`、TNS `0 ns`、0 setup failing endpoints；
- top 20 path 已不再包含 TLB；当前最差路径为乘法器相关路径，slack `+0.419 ns`；
- 该结果是 standalone CPU top，不含官方 SoC placement、routing 和板级 XDC，不能证明
  完整设计已经在板上闭合 100 MHz。

## 决策门禁

本轮通过所有本地功能和生成门禁，且没有改变 `func_lab19` 周期数。提交并推送候选后，
必须用精确 commit 构建锁定的 `perf20@100MHz` 完整 SoC：

- 若 routed WNS 非负，才执行三次真实 `perf20`，取最低一次作为性能决定性结果；
- 若 routed WNS 仍为负，不能进行板测或声称时序闭合，继续按 routed top path 设计下一轮
  窄寄存边界。

功能通过、板测通过和时序闭合始终是三项独立结论。

## 精确提交的完整 SoC 结果

提交 `26925beb9bbe70ae3312da39e39fc7fefbc3e133` 推送后，使用 Vivado 2023.2、
官方 `perf20` profile 和 100 MHz 目标完成了锁定的完整 SoC implementation：

- bitstream 成功，DRC 0 error；
- setup WNS/TNS 为 `-0.170742/-8.018137 ns`，122 个 failing endpoints；
- hold WNS 为 `+0.051 ns`；
- `.fpgajob` 为 `D:\fpga-eval-artifacts\26925be-perf20-tlb-walk-result-100mhz-v1.fpgajob`，
  SHA-256 `47B24F2AA04320FF7324F8CE9C993D1018C54A063D57D0489128FB1BE7921D42`；
- timing summary SHA-256
  `73FE5822C07F76F8B2BDAA0023A3F3E55B4667C2CA0997EC428DC5C08F4647D3`。

原主 TLB 到 exception 的最差路径已经消失。新的最差 CPU 路径从 L1I response
predecode 寄存器出发，经 response-level prediction correction 和 predictor flush，到
speculative RAS restore；数据延迟 `9.801 ns`，logic/route 分别为 `3.074/6.727 ns`。
因此本轮改善有效但尚未闭合，且不能提交远端板测。下一轮按 ysyx 的寄存
`fixRedirect` 边界隔离这条恢复路径。
