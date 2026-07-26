# LSQ 已选 load payload 寄存

日期：2026-07-27

## 目标与起点

紧凑年龄顺序 IQ 提交 `b5d020ecbf91a60fa52d0d21fc07d8a8fa0b02d6` 在锁定的
Vivado 2023.2 完整 SoC 100 MHz 实现中成功生成 bitstream，DRC 0 error，但 WNS
`-0.584979 ns`、TNS `-167.869400 ns`，仍有 1114 个 setup 失败端点。最差路径从
LSQ `loadHead_reg[1]` 出发，经动态 load entry payload 选择、store-order/forwarding 和
completion 数据生成，到 `completion_data_reg[6]`；10.425 ns 数据路径中 7.765 ns
（74.5%）为布线。

ysyx `la32r-linux` 的 LoadQueue 在选择边界寄存完整 AGU uop，而不是只寄存队列索引。
本轮采用相同的结构原则，但保留当前实现所需的易变队列状态检查。

## 实现

- 新增 `OooScheduledLoad`，保存所选 load 的 ROB generation、目标物理寄存器、虚拟地址、
  size、byte mask、符号扩展和 LL 属性。
- scheduler 在寄存 `loadHead` 的同一边界寄存上述不可变 payload；翻译请求、store age/
  overlap 检查、cache request 和 forwarding completion 均消费该寄存 payload。
- `valid/addressReady/requestSent/completed/translationDone/physicalAddress/uncached` 仍从
  `loads(loadHead)` 的窄易变状态读取，并用 ROB pointer 再次核对槽位身份，防止复用槽位
  或已发请求被陈旧快照误用。
- AGU 与 scheduler 同拍命中同一 load 时，把新地址和元数据直接旁路进 scheduled payload，
  不增加正常地址生成到翻译请求的周期。
- flush 清除 scheduled valid；已有 store ordering、forwarding、translation ownership、
  response tag 匹配和多 outstanding load 规则保持不变。

全部 CPU 逻辑只修改 Scala/SpinalHDL；`rtl/mycpu_top.v` 由生成器重新产生，没有手工
Verilog。

## 功能回归诊断与修复

提交 `26ec431da4773b07c8d92ece744a507bb1bd1dd9` 的 100 MHz `perf20` 板测在 20 项
上全部超时，而同一提交的 `func58` 通过。进一步在完整 Chiplab SoC 仿真中定位到：不可
反压的 cache load response 与已就绪 store completion 同拍时，completion payload 仲裁由
load 获胜，但 store 仍被错误标记为 `completed`。该 store 此后不会重试，ROB 则永久等待
从未发出的 store completion。

修复将“store completion 候选”和“store completion 实际发出”分离。只有本拍没有 cache
response 和 load forwarding 占用 completion 端口时，store 才发出 completion 并置
`completed`；冲突时 store 保持 pending，下一拍自动重试。新增定向测试构造同拍 load
response/store completion 冲突，检查先完成 load、下一拍再完成 store。

## 本地证据

| 检查 | 结果 |
| --- | --- |
| Scala/Spinal/Verilator | 36 suites，127/127 passed |
| LSQ 定向测试 | 15/15 passed；新增 load response/store completion 冲突重试覆盖 |
| Python repository gates | 362/362 passed |
| package/port/Yosys/publish | 全部通过；官方 49-port 合同不变 |
| exact generated-top lint | 852 项，仅 `UNUSEDSIGNAL`/`CMPCONST`；签名 `cfd92c9f9503099b2269ec97abc7023886b9e4fabc4cef0d43f7aa9f6ea1613b` |
| generated RTL | SHA-256 `8fba51e050c9bfce82dbf66ee638ad908e3c69df70810fe1eb8d314bc44835b7` |
| 完整 Chiplab SoC bitcount | PASS；SoC count `0x53e10`（343,568），进入官方 `test_finish` |
| 前一生成版本 standalone Vivado 2023.2 | WNS `+0.359 ns`、TNS `0`、0 failing endpoint；当前精确 RTL 待完整 SoC 构建 |

LSQ 从 2,004 LUT / 2,157 FF 变为 2,039 LUT / 2,217 FF，即 +35 LUT / +60 FF。
上一版 LSQ 最差路径不在 standalone top 20；最差路径回到既有 L1I predecode 到 BRAM
enable。报告 SHA-256：

- timing：`1570c31ab4bd011247b41b8aaef4b912563e059b7e495684d10b7cd2854dab4f`
- utilization：`fda6160d61a100e046200226bd39fb540af83c049a48fd3b4ced9a67e5e49b17`
- DRC：`56fe6bf48582d84ce2967d0debe085b70230ca1290dbc9011061b17d06f1e2cc`
- DCP：`4d172efd3fdb6b214c502d04778323a2cb37387e3325ec7e8a65450b89128b12`

standalone DRC 的 NSTD-1/UCIO-1 来自未加载板级 XDC，不能作为完整 SoC DRC 结论。

## 后续决定门禁

修复后的精确 RTL 尚未获得完整 SoC route 或真实板测结果，因此不能声称 100 MHz
闭合或性能提升。提交并推送后直接构建显式 `perf20@100MHz` 包；若负 WNS，仍按 advisory
策略分别报告 timing not met 与板测结果。按当前测试策略，先完成三次真实 `perf20` 并取
最低总用时；只有 `perf20` 暴露功能问题时才回到 `func58` 定位。

## 规则审核

改动只调整通用 LSQ 管线边界，不依赖测试程序、外部答案、未声明存储或仿真专用行为；
官方顶层、ISA 精确顺序、store 副作用提交边界和 4 发射/5 回写/3 提交合同不变。生成 RTL
及精确 lint 签名均由仓库门禁锁定，符合仅由 Scala/SpinalHDL 生成 CPU RTL 的要求。
