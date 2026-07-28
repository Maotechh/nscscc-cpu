# Quicksort recovery and registered store release

日期：2026-07-28

## 目标与结论

本轮在提交 `c1103dc003ec71a13f0678d11a8192de139cdf9f` 的通用 cache response epoch
修复基础上，以提交 `724b808959957c27fc64bda36b8c5cb828f51c8b` 寄存已接受 store 的释放动作，
切断 LSQ 到 L1D MSHR 的组合关键路径。最终三次真实 `perf20@100MHz` 均为 20/20 PASS，
包括此前失败的 `quick_sort`。最低总 SoC 计数为 `73,826,502`，即 `0.73826502 s`，
相对原始基线 `206,902,887` 个周期达到 `2.8026x` 加速。

## Quicksort 根因与复现纠正

此前本地复现错误地复用了 allbench 的 `ram.dat`。该镜像依赖拨码选择测试，并不是独立
`quick_sort` 镜像：PC `0x1c0003dc` 的指令为拨码读取 `0x157f5fec`，而独立镜像在同一位置
应为调用 `shell6` 的 `0x5400d400`。旧 testbench 还只在 END_PC 出现在最后一个提交槽时退出，
三提交核可能已进入 `test_finish`，但因 END_PC 位于较早提交槽而继续运行。

从官方 `software/examples/nscscc_perf/obj/quick_sort/inst_data.bin` 机械生成独立 byte-oriented
`ram.dat` 后，随机 AXI 延迟 seed `5570815` 下观察到 PASS-only PC `0x1c0005f0`，未观察到
ERROR-only PC `0x1c00069c`，且 NEMU DiffTest 无错误。该纠正说明当前候选并没有新的 quicksort
回归；真实板测随后给出了决定性验证。

## 实现

- cache request/response、L1D hit/MSHR waiter/refill 和 uncached AXI read context 携带
  `recoveryEpoch`，LSQ 只接受 ROB pointer 与 epoch 同时匹配的 load response，防止 recovery 后
  旧 DDR 响应命中新近复用的 ROB/LDQ 槽位。
- store request 被 L1D 接受时立即推进 `storeHead`，并记录 `acceptedStoreIndex`；下一拍再清除
  store entry 并向 allocator 发出 release pulse。
- failed SC 的释放和 accepted-store sidecar 串行化，保持一次只释放一个 LSQ 槽位。
- 修改只发生在 Scala/SpinalHDL 源码；`rtl/mycpu_top.v` 由仓库生成流程自动产生，没有手写或
  手改 Verilog。

## 本地门禁

| 检查 | 结果 |
| --- | --- |
| LSQ 定向测试 | 16/16 passed |
| Scala/Spinal/Verilator 全量 | 36 suites，131/131 passed |
| Python repository gates | 362/362 passed，10 项既有 skip |
| port/Yosys/publish | 全部通过 |
| generated-top lint | 精确 844 条既有 warning，0 unexpected |
| 生成 RTL SHA-256 | `a4b59fd78577ac74275f5f93297b7b7796ebe8b61c6194565e076940623fb68c` |
| standalone Vivado 100MHz | WNS `+0.279 ns`，TNS `0 ns` |

## 完整 SoC Vivado 2023.2

- profile：`perf20`；器件：`xc7a200tfbg676-2`；目标/实际 CPU 时钟：`100/100.000000 MHz`。
- implementation 与 bitstream 成功，DRC 0 error。
- WNS/TNS：`-0.092101/-0.661442 ns`，`timing_met=0`，策略为 advisory。
- 相比上一版 `-0.205288 ns`，WNS 改善约 `0.113 ns`；原 LSQ store-release 最差路径已消失。
- 新最差路径从 `L1D misses_0_state_reg[1]` 到 `misses_3_refillMask_reg[5]`，经过 L1D MSHR
  lookup、L2 write-ready/tag lookup 和 L1D refill control，共 14 级逻辑；数据路径 `10.007 ns`，
  其中布线 `7.639 ns`（76.336%）。
- `.fpgajob` SHA-256：
  `49c8f6111272382591c91f33910044bf8b6f8b07c4ecbc9f51c07aeba40137dc`。

完整构建工作区位于 `D:\flw\job-3463712585`，评测包位于
`D:\fpga-eval-artifacts\724b808-perf20-store-release-cut-100mhz-v1.fpgajob`。

## 三次真实 perf20

| 次数 | Job ID | 结果 | SoC count | 100MHz 用时 |
| ---: | --- | --- | ---: | ---: |
| 1 | `20260728-071326-b9277229` | 20/20 PASS | `73,826,507` | `0.73826507 s` |
| 2 | `20260728-071808-f9db63b0` | 20/20 PASS | `73,845,516` | `0.73845516 s` |
| 3 | `20260728-072205-af6feb81` | 20/20 PASS | `73,826,502` | `0.73826502 s` |

三次均满足：FPGA programming PASS、board verdict PASS、20 项 `correct_flag=1`，下载的
`programming-summary.txt`、`board-summary.txt`、`perf_vio.csv`、`vivado-metrics.txt`、
`check_timing.rpt`、`drc.rpt`、`timing_summary.rpt` 和 `utilization.rpt` SHA-256 全部与服务端
`artifacts_sha256` 一致。证据目录分别为：

- `D:\fpga-agent-client\results\20260728-071326-b9277229`
- `D:\fpga-agent-client\results\20260728-071808-f9db63b0`
- `D:\fpga-agent-client\results\20260728-072205-af6feb81`

三次结果都包含同一条 warning：compiled design 的 WNS 为 `-0.092101 ns`。因此可以报告真实
板测 PASS，但不能报告 100 MHz timing closure。

## 合规与决策

修复使用通用 transaction epoch 和队列释放时序，不识别程序名、PC、数据值、拨码值或 benchmark
地址，不修改官方测试、计数器语义、Chiplab reference 或板级约束。RTL 由 Scala/SpinalHDL 自动
生成，符合禁止手写优化 Verilog 的仓库约束。

真实性能相对 `baseline.txt` 超过 2 倍，且三次功能均满分，因此保留并推送
`724b808959957c27fc64bda36b8c5cb828f51c8b`。下一轮优先拆分 L1D/L2 MSHR refill-ready
组合链，目标是在不增加 miss 服务周期的前提下消除剩余 `0.092 ns` setup violation。
