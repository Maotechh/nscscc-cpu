# LSQ 调度边界与 L1D refill 合并修复

日期：2026-07-27

## 本轮目标

本轮从提交 `b5d020ecbf91a60fa52d0d21fc07d8a8fa0b02d6` 开始，先缩短 LSQ 动态
load payload 选择路径，再处理真实 `perf20` 暴露的功能错误。CPU 仍保持 4 发射、5 回写、
3 提交以及 64 B L1/L2 cache line；所有 CPU RTL 只由 Scala/SpinalHDL 生成。

## 已完成的结构改动

- 新增 `OooScheduledLoad`，在 load scheduler 边界寄存 ROB generation、目标物理寄存器、
  地址、size、byte mask、符号扩展和 LL 属性。
- translation、store age/overlap、cache request 和 forwarding completion 消费寄存后的
  payload，避免 load entry 大范围动态选择直接进入 completion 关键路径。
- AGU 与 scheduler 同拍命中同一 load 时提供旁路，不增加正常地址生成到翻译请求的周期。
- 修复 cache load response 与 store completion 同拍冲突：store 只有真正占用 completion
  端口后才置 `completed`，冲突时下一拍重试。

## 板测失败现象

提交 `c3373fafaa4ea3c0f7c145cf234ec4ff8fce56b5` 的板测结果如下：

| profile | 时钟/时序 | 结果 |
| --- | --- | --- |
| `func58` | 100 MHz，WNS `-0.426965 ns` | 通过，VIO `3A00003A` |
| `perf20` | 100 MHz，WNS `-0.558956 ns` | 13 pass、5 fail、2 timeout |
| `perf20` 诊断 | 约 32.73 MHz，WNS `+0.977809 ns` | 14 pass、3 fail、3 timeout |

降低频率后 `fireye_B2`、`inner_product`、`my_memcmp` 仍失败，因此负 WNS 不是唯一原因。

## 精确根因

使用官方 `my_memcmp` image 和 NEMU DiffTest，首个错误出现在 PC `0x1c001050`：
`ld.bu` 从 `0x1c080c41` 读取时，NEMU 为 `3`，DUT 为 `0`。追踪 LSQ、L1D MSHR 和
refill beat 后确认有两个重复移位错误：

1. LSQ 的 4-bit store byte mask 已按 32-bit word 内地址对齐，L1D 构造 64 B line mask
   时又按完整 line byte offset 移位，导致地址 `...c41` 的 mask 从 bit 1 错移到 bit 2。
2. pending store 与 refill beat 同周期时，8-byte beat mask 又按地址 bit 2:0 移位；字内
   bit 1:0 被第二次编码，refill 数据因此覆盖刚写入的字节。

修复后，line mask 只按 word 在 64 B line 中的位置移动，beat mask 只用地址 bit 2 选择
64-bit beat 的低/高 32-bit word。`pendingStoreAddress[1:0]` 不再参与第二次移位，这是新增
一条 `UNUSEDSIGNAL` lint 的预期原因。

## 定向验证

新增 L1D 测试覆盖三种 byte store：

- refill 前写地址 `0x100`，mask `0x1`；
- refill 前写地址 `0x101`，mask `0x2`；
- store apply 与 refill beat 同周期写地址 `0x102`，mask `0x4`。

零数据 refill 完成后，word load 必须得到 `0x00030303`。L1D 定向测试 9/9 通过。
相同官方 `my_memcmp` 对拍从原来的约 9.2 万条首错推进到 1,161,231 条提交无失配；停止
原因是 500 万周期诊断上限，不是 DiffTest mismatch。

## 本地门禁

| 检查 | 结果 |
| --- | --- |
| Scala/Spinal/Verilator | 36 suites，128/128 passed |
| Python repository gates | 362/362 passed |
| package/port/Yosys/publish | 全部通过，官方 49-port 合同不变 |
| exact generated-top lint | 853 条，仅 `CMPCONST`/`UNUSEDSIGNAL` |
| lint signature | `5c7dc1c4b5d8261b216d5a2222fef205d17d133ad9175ad18efc188e3985e836` |
| generated RTL SHA-256 | `47b7759a644976535630f03610eea605d7417de34c73ef73395d98cfcfbb64d7` |
| standalone Vivado 2023.2 | 100 MHz synth 通过，WNS `+0.359 ns`，TNS `0` |

Standalone 综合使用 `xc7a200tfbg676-2`、`general.maxThreads=8`，0 synthesis error、
0 synthesis critical warning。没有加载板级 XDC，因此 DRC 中的 `NSTD-1`/`UCIO-1` 仅表示
顶层端口未约束，不能替代完整 SoC implementation DRC，也不能证明 place/route 时序闭合。

综合证据 SHA-256：

- timing report：`726199d9319650f3a8bf7e05c321ebf00ed7da6e612d73f5ded2016e7fccdcfe`
- utilization report：`18ed386c6396057b7afb9e6d14b9a6083f05f652c7a27842650f40aeca5a2e51`
- DRC report：`4adb78bd0233ec61f6476b709b1fe5cb799d9f1e153403128420d1782bf1692d`
- synthesized DCP：`6b889c516dec4fd2ef735a7b5949acf8ebb4531749924c40236373a61dd8e04a`

## 规则审核与下一门禁

改动是通用 cache store/refill 一致性修复，不读取测试程序身份、答案或外部未声明状态；
没有手写 CPU Verilog。`rtl/mycpu_top.v` 与 replacement/lint 锁由同一确定性生成流程同步。

下一步提交并推送精确候选 commit，构建 `perf20@100MHz` 完整 SoC `.fpgajob`，验证完整
implementation、DRC、WNS 和板测。按流程执行三次真实 `perf20`，以三次中最低完整程序
时间作为性能判断；只有 `perf20` 再暴露功能问题时才回到 `func58` 定位。
