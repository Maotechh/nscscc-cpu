# dev 迭代 003：MEM 到 Decode 的分支结果前递

## 状态与边界

- 开发分支：`dev`，工作树父提交 `ab9fd9978deab6b41ff0fe9146a0abe7ed79ce8c`。
- 用户对 `AGENTS.md` 的未提交修改保持隔离，未覆盖、未暂存、未进入评测对象。
- 本轮建立了不移动分支或主索引的只读评测对象 `f3ce32ce6823396746845659bbe46076fea93083`。
- 本轮建立了不可变 perf20 包，但真实板卡有效样本仍为 **0/3**；首次远端任务在编程阶段遭遇外部 JTAG 锁占。
- 因没有有效板测，本轮不提交性能 commit，也不声称真实硬件性能已经提升。

## 分析依据

先用与迭代 002 完全相同、启用 `RUN_C + TRACE_COMP + DiffTest` 的 Verilator 模型对 perf20 做两层采样：

1. 全程架构计数器，用来排除 ICache、DCache 或分支猜测的错误归因；
2. 以 perf20 读取计时器的边界作为计分窗口，只统计真正决定成绩的区间。

迭代 002 的计分窗口累计出现 4,487,896 个 Decode 分支依赖停顿。源码审计发现，Decode 的普通操作数支持 MEM 前递，但分支比较值只接受 EX 前递；当生产者已经在 MEM 且结果完成时，分支仍固定等待写回。这是可直接消除、又不改变 Cache 或 ISA 行为的结构性浪费。

原始基准与候选 CSV 分别保存在：

- `logs/dev/evidence/iteration-003/perf20-scored-window-reference.csv`
- `logs/dev/evidence/iteration-003/perf20-branch-forward.csv`

## 实现

1. `DecodeStage` 增加默认关闭的 `memoryBranchForwardingEnabled` 开关，Legacy 叶级生成器维持原周期合同。
2. 完整 CPU 同时启用 late-result forwarding 和 MEM branch forwarding。
3. 分支源值按“EX 最新生产者 → MEM 已完成结果 → 寄存器堆”选择，避免旧结果覆盖年轻生产者。
4. MEM 命中仅在 `dependencyNeedsStall` 为真时阻塞；结果完成后同拍完成分支比较或 JIRL 目标形成。
5. 保留迭代 002 的分支握手修复：Decode 被 EX 背压时不允许 redirect 逃逸，只有 payload 真正离开 Decode 的周期才驱动 Fetch。
6. 新增单元测试覆盖“MEM 结果未完成时停顿、完成同拍前递并 redirect”，以及 backpressure 下 redirect 不提前发出。

所有 CPU 行为修改均位于 SpinalHDL/Scala。`rtl/mycpu_top.v` 来自锁定生成器和 `core_top_gate package` 的机械发布，没有手写 Verilog。

## 生成与门禁

- 锁定版本：JDK 17.0.19、Scala 2.13.16、SBT 1.10.11、SpinalHDL 1.14.2。
- 两次独立生成一致；原始 RTL SHA-256 为 `6d39fd9899392505522dfe2aad83bffafa69d7197811b9bd554492478c5ec74f`。
- 发布 RTL SHA-256 为 `b51160dfeaafbec3784e485f79d1a05b97e3f0083de632280b18d8a436c9c5fd`，867,503 字节。
- Scala：19 suites、33 tests 全部通过。
- Python：391 passed、10 skipped。
- 49 端口合同、publish-check、typed AXI boundary、candidate closure、replacement reachability、port-check、严格零 warning Verilator lint、Yosys check 全部通过。
- `git diff --check` 通过。

## 功能测试

锁定 `func/func_lab19` 镜像 SHA-256 为 `b916b85553da2795d6d80332c40056f960c6c4fd36ae341eb7d8cf494b26281e`，总线随机种子 5,570,815。严格 `RUN_FUNC + TRACE_COMP` 结果：

- `END by Syscall`
- `Reached test end PC.`
- 无 DiffTest mismatch
- 608,070 周期
- 174,129 条指令

一次使用 perf20 的 `RUN_C` 测试台直接运行功能镜像的诊断被明确作废；该测试台不具备功能异常序列的参考模型语义，未计入门禁。

## 本地 perf20 结果

| 指标 | 迭代 002 | 迭代 003 | 结果 |
|---|---:|---:|---:|
| 20 项总周期 | 54,590,252 | 52,267,170 | 1.044446× |
| 计分窗口周期 | 41,802,849 | 39,461,758 | 1.059326× |
| 分支依赖停顿 | 4,487,896 | 2,102,638 | -53.1487% |
| 胜 / 退化 | - | 18 / 2 | - |

最大总周期收益为 select_sort 1.2708×、CRC32 1.1880×、minmax 1.1474×、bubble_sort 1.1405×。`stream_copy` 和 `inner_product` 分别轻微退化 0.0486% 与 0.0037%，作为后续负控保留。

总指令数增加 22,194，其中 stringsearch 的 UART 轮询区间增加 22,209，发生在其 570 个计分窗口之外；CoreMark 少 15 条。20 项均 DiffTest clean，因此只把周期变化解释为微结构时序效果，不解释为程序语义变化。

相对迭代 002，本轮本地总周期加速为 1.04445×；相对迭代 002 之前的本地参考总周期 55,098,455，累计为 1.05417×。证据不支持 2×、5× 或 100× 声称。

## Vivado 2023.2

隔离评测对象 `f3ce32c` 在锁定 chiplab `a2e11b3`、myCPU gitlink `aa3bde1` 和 `xc7a200tfbg676-2` 上完成综合、实现与 bitstream：

| 项目 | 结果 |
|---|---:|
| WNS / TNS | +0.410125 ns / 0 ns |
| WHS / THS | +0.052 ns / 0 ns |
| Slice LUT | 22,977 |
| Slice Registers | 23,790 |
| BRAM tiles | 36.5 |
| DSP | 8 |
| no_clock / unconstrained internal endpoints / loops | 0 / 0 / 0 |
| DRC Error / Critical Warning | 0 / 0 |

相对迭代 002 仅增加 23 LUT，寄存器、BRAM 与 DSP 不变。包内 8 个 manifest 文件的长度和 SHA-256 均逐项验证一致。

最终包：

- `D:\fpga-agent-client\jobs\iteration-003-f3ce32c-perf20.fpgajob`
- SHA-256 `c034ec856cb57107dc9c7c83b5f7cd665c3b9c4b58fa1f6d2bd42423aa47a5ab`
- 1,056,649 字节

## 真实板卡

首次任务 `20260718-041502-7d6d47fe` 的包哈希、source commit、Vivado、器件和参考锁均被服务器正确识别，但在 programming 阶段终止：

```text
ERROR: [Labtoolstcl 44-494] There is no active target available for server at localhost:3121.
Target jsn-JTAG-SMT2-210251A08870 may be locked by another hw_server.
```

任务没有 `programming-summary.txt`、`board-summary.txt` 或 `perf_vio.csv`，故为无效样本，不能计入所需三次烧录，也不能判断性能。按评测 skill 约束，不使用管理员凭据、不切换 maintenance、不绕过锁定服务。

## 规则审核与决定

- 修改范围是允许的流水线与前递微结构；未修改测试程序、计时器、VIO 判据、时钟约束或远端服务。
- ICache/DCache 容量与组织未改，继续满足各至少 8 KiB 的规则要求。
- 仓库中唯一 CPU RTL 是锁定 SpinalHDL 生成并机械发布的 `rtl/mycpu_top.v`；纯 Spinal candidate closure 通过。
- 真实板卡没有有效样本，因此不满足性能 commit 条件；当前不 commit。
- 本地功能、perf20、时序均通过且有明确收益，所以不回退；保留不可变包等待板卡恢复，并继续分析下一项独立可开关优化。

## 下一轮优先项

1. 把剩余 2,102,638 个分支依赖停顿按生产者阶段与指令类型细分。
2. 检查分支预测修复/BTB 更新的固定气泡，优先选择不增加 Decode 关键路径的结构。
3. 评估 DCache miss/AXI 等待能否与独立执行重叠，但以 inner_product、stream_copy 为负控，防止对存储瓶颈误归因。
4. 板卡释放后对完全相同的包取得三次有效样本，取最慢一次作为决定性结果。
