# 裸机 Load-to-use 直映旁路与早唤醒

日期：2026-08-04

## 目标与依据

本轮只优化裸机性能程序的 Load-to-use 延迟。CRMD 处于直映模式时，原实现虽然不查 TLB，
仍会经过数据翻译请求、寄存响应和 LSQ 接收；Load 数据返回后还会依次经过 LSQ completion
寄存和 ROB accepted-completion 寄存，依赖指令才被唤醒。

参考 ysyx `la32r-linux` 的 `LoadResultBuffer.OUT_zeroCycleForward` 和 IssueQueue LSU wakeup，
本轮建立 Load 数据早唤醒路径。分页、DMW、精确异常、ROB completion 和提交路径保持原语义。

## 实现

- `OooCoreSystem` 从已寄存的 CRMD/DATM 上下文派生动态直映属性。只有
  `DA || !PG` 的普通 Load 允许跳过翻译请求；分页模式和 DMW 继续经过翻译单元。
- LSQ 在直映模式直接使用虚拟地址作为物理地址，并采用 DATM/cache-disable 属性进入现有
  request buffer。Store、LL/SC、CACOP 和所有分页异常路径不变。
- Cache response 只有在同时匹配有效 LDQ entry、ROB pointer 和 recovery epoch，且无总线错误
  时，才产生专用 `pdst + data` Load wakeup。Store-to-Load forwarding 复用同一成功路径。
- Load completion 先进入 LSQ 已有的结果寄存器，下一拍写入 PRF 和 ready map，并通过既有
  五路 wakeup 标签总线唤醒
  resident/enqueue IQ 与 Store-data queue。原 LSQ/ROB completion 仍负责精确完成、异常、提交
  和恢复；该路径比 ROB 正式唤醒早一拍，稍后的普通写回是幂等的。
- Load 数据复用已有 LSU PRF 写端口，不增加第六个 PRF 写端口。LSQ completion 和 ROB wakeup
  固定相差一拍；一级 `valid + pdst` 窄标签寄存器只允许已提前写入的幂等 Load completion
  给新 Load 让出端口。SC、异常和先前因冲突未提前写入的 Load 仍保持正式
  completion 优先级。
- 早唤醒只在 Scala/SpinalHDL 源码实现；`rtl/mycpu_top.v` 由仓库生成流程自动更新，没有手改
  Verilog。

## 本地门禁

- 定向测试覆盖：直映 Load 不发 translation request、物理地址/属性旁路、原始 cache response
  早唤醒、分页仍发 translation request、错误响应不早唤醒、旧 recovery epoch 不早唤醒。
- Scala/SpinalHDL：38 suites，164/164 passed。
- Python：364/364 passed。
- 49-port contract、Verilator lint、Yosys structure、publication consistency：passed。
- Verilator 审核 warning：845，仅 `CMPCONST`/`UNUSEDSIGNAL`，精确签名
  `48bc21786139a637214eb7b221a1bb6b48fd70fc4e52ec9775230bb77d33f3d7`。
- 自动生成 RTL SHA-256：
  `692d2861b78bf9ee34c0aaa184f718e2b877ec9b9a7331cfdba9b7ba2fcdcda7`。
- `docs/refactor/status.yml` 记录的 `make cpu-check` 在当前 Makefile 中不存在。本轮采用真实入口
  `make all port-check lint yosys-check publish-check`，该文档漂移留待评测结果确定后统一修正。
- `scalafmtCheckAll` 仍报告仓库已有的 16 个未格式化文件，其中本轮触及 3 个；未批量格式化
  无关源码，功能和发布门禁不受影响。

按用户要求，本轮没有运行本地 perf20。候选将直接构建 `perf20@100MHz` 完整 SoC 并在真实
实验箱评测；只有硬件失败时才回到本地复现。

## 首次物理实现与结构修正

首版候选 `297ac34b77c58c56583956ad37d7daf06fee04fb` 使用独立的第六个 PRF 写端口和独立的
Load wakeup 比较端口。`perf20@100MHz` 构建在 `D:\flw\job-335626198` 完成综合和
phys_opt，但没有完成 route/bitstream：

- placed `LUT as Logic = 90,543`，相同统计口径下最近闭合工程为 84,429；
- post-phys_opt `WNS = -3.441 ns`、`TNS = -69,660.891 ns`；
- route Phase 1 长时间单线程运行，最终被客户端 7,200 秒构建超时终止，没有生成可提交包。

该结果不能作为功能或性能证据。分析确认独立 PRF 写端口把额外数据选择复制到全部物理寄存器，
独立 Load tag 又扩大 IQ、rename-ready 和 Store-data queue 的比较网络。当前修正撤掉这些端口，
改为 LSU 写回槽复用和两级窄标签流水线；自动 RTL 从首版 5,396,113 字节降至 5,350,742 字节。
修正后 Scala 主/测试源码编译通过，49-port、Verilator lint、Yosys structure 和 publication
consistency 再次通过；warning 数量与签名均未变化。新一轮 Vivado 与真实板测结果另行记录。

第二版候选 `e7aac030cd799d932671fd74a6f61fc2c6b90b58` 已消除第六写端口，但仍将 LSQ 的
组合 `generatedCompletion` 直接扇出到 IQ。`perf20@100MHz` 构建在
`D:\flw\job-2308248847` 完成综合和布局后停止，未进入 route/bitstream：

- 综合 0 errors，用时 6 分 10 秒，Slice LUT 从首版 87,220 降至 84,666；
- placed `LUT as Logic = 87,622`、寄存器 53,760；
- post-place `WNS = -5.638 ns`，phys_opt 中间结果仅改善至 `-5.600 ns`，不具备继续布线价值；
- placed checkpoint 的 20 条最差 setup 路径全部从
  `scheduledLoad_virtualAddress` 经过 partial-overlap/completion 仲裁和 Load wakeup，终止于
  IQ entry 的 CE/D；最差数据路径 15.318 ns、22 级逻辑，其中 route 12.104 ns（79.018%）。

当前第三版把早唤醒资格与 `pdst/data` 一起放在 LSQ completion 寄存边界之后，复用已寄存的
completion payload，再从该寄存边界进入 PRF/IQ；后端幂等冲突跟踪相应缩成一级标签。自动 RTL
为 5,350,584 字节。Scala 主/测试源码编译、49-port、lint、Yosys 和 publication 门禁通过，
warning 仍为 845 条且签名不变。该版本需要重新进行完整 Vivado implementation 和真实板测。

## 尚未成立的结论

当前没有新的 Vivado implementation、bitstream、WNS 或真实板测证据，不能声明性能提升、
100 MHz 时序闭合或 perf20 功能满分。候选 commit 仅用于远端构建和真实评测身份固定。

## 合规审核

优化是通用的运行模式与事务身份判断，不识别程序名、PC、数据值、拨码值或 benchmark 地址；
不修改计数器、官方测试、Chiplab reference、XDC 或主频定义。CPU 逻辑只改
Scala/SpinalHDL，发布 Verilog 完全自动生成，符合当前仓库和比赛约束。
