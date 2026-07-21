# 数据侧 direct/DMW 翻译旁路

日期：2026-07-21

## 选择依据

上一提交在固定 `func/func_lab19` 下为 743,893 clocks。跟踪 LSU 请求后发现，direct/DMW 模式仍经过与分页 TLB 相同的 pending 往返；同时 load 地址翻译被未解析的老 store 地址完全阻塞。地址翻译本身没有内存副作用，因此可以提前，但 D-cache 请求和 forwarding 判定仍必须服从 LSQ 顺序。

## 未采用方案

* 直接从 completion 组合产生同拍 ROB recovery。Scala 85/85 通过，但官方 DiffTest 在 31,705 instructions 后出现 PC/GPR mismatch，已完整撤销。
* 指令和数据两侧同时旁路 direct/DMW 翻译。Scala 85/85 通过，但官方测试在中断处理路径 `0x1c00f064` 出现 ERA/CSR 可见性错误。结论是指令侧不能跨过现有 privileged 状态边界，本轮只保留数据侧旁路。
* 最初的数据侧旁路功能通过，计数为 738,572 clocks，但 Vivado WNS 为 `-0.480 ns`、TNS 为 `-7.328 ns`，因此不能作为可接受版本。

## 最终设计

* `OooAddressTranslationUnit` 对数据侧 direct/DMW 请求直接寄存响应，复用统一的物理地址和 memory attribute 计算；分页请求继续走 TLB search pending 路径。
* LSQ 允许无副作用的 load translation 与未解析的老 store 地址窗口重叠。
* store-order、地址重叠、forwarding、D-cache/uncached 请求和完成条件保持原有门控，提前翻译不会提前产生内存副作用。
* 定向测试覆盖“老 store 地址未知时翻译已发出，但 cache request 和 load completion 均未发生”。

## 性能结果

固定 `func/func_lab19`、NEMU DiffTest、bus delay seed `5570815`：

| 配置 | Instructions | Clocks | IPC |
| --- | ---: | ---: | ---: |
| 上一提交恢复训练表 | 131,226 | 743,893 | 0.176404 |
| 数据翻译旁路与 LSQ 解耦 | 131,225 | 737,817 | 0.177856 |

相对上一提交减少 6,076 周期（0.817%）；相对关闭静态预测的公平基线 783,358 clocks 减少 45,541 周期（5.81%）。候选到达 end PC，以 `END by Syscall` 结束，NEMU DiffTest 无 mismatch。

## 验证与综合

最终生成 RTL SHA-256：
`c0282ca0e6e2fe58832ff7e8f43e452c0e645706002673f1f51d8b4cc6a72231`。

| 检查 | 结果 |
| --- | --- |
| Scala/Spinal/Verilator | 35 suites，85/85 passed |
| Python repository tests | 362/362 passed |
| package、port、lint、Yosys、publish | 全部通过 |
| Chiplab `func_lab19` | 通过；737,817 clocks，IPC 0.177856 |
| Vivado 2023.2 | 0 synthesis errors；100 MHz WNS `+0.419 ns`，TNS `0`，0 failing endpoints |
| 最差路径 | backend issue operand 到 multiplier result，data path delay 9.460 ns |
| 资源 | 71,765 LUT，39,578 FF，42 RAMB36，12 RAMB18，4 DSP |

## 合规与限制

CPU 修改全部位于 Scala/SpinalHDL；发布 RTL 由生成流程重建并保持 Git ignore，没有手写 Verilog、软件地址识别、DiffTest 绕过或 false path。当前没有真实 FPGA 上板环境，因此本轮只采用官方仿真周期作为性能证据，不声明板上加速比。
