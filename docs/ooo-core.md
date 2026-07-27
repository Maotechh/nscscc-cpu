# 4 发射 / 3 提交乱序核交接说明

本文是当前 `dev-OoOE` 分支的单一架构和验证入口。代码由 Scala/SpinalHDL 生成，权威生成产物是 `build/core_top/package/rtl/mycpu_top.v`；Git 跟踪的 `rtl/mycpu_top.v` 是供 Chiplab、Vivado 和远程构建器使用的同内容发布镜像，不是手写 Verilog 的第二份实现。

## 状态与基线

当前官方顶层已经实例化 `openla500.core.OooCoreSystem(OooCoreConfig.FourIssueThreeCommit)`。旧 `SpinalCoreBackend` 和 `openla500.pipeline` 不再参与生成；保留下来的少量 `OpenLa500*` leaf 模块仅供仍被 OoO 核复用的 ALU、乘除法、CSR、TLB 或独立合同测试使用。

当前本地验证候选（2026-07-27，生成 RTL SHA-256 `3b4adddff81c8978bbefdcfe38c44792a34fa8437dfd8db85a641bb181cc4263`）如下：

| 检查 | 结果 |
| --- | --- |
| Scala/Spinal/Verilator | 36 suites，130 tests，130 passed，0 failed，0 aborted |
| Python repository gates | 362 tests，362 passed，0 failed/error |
| core_top package/port contract | pass，49 ports，17 inputs，32 outputs，`TLBNUM=32` |
| Verilator complete-top lint | pass，853 条精确签名审计后 closure 为 0 warning/error |
| Yosys 结构检查 | pass，Yosys 0.33，无 warning/skip |
| 当前精确 RTL 的 chiplab `func/func_lab19` | DiffTest pass，`END by Syscall` 并到达 end PC；139,668 instructions / 552,247 clocks / IPC 0.252909 |
| 当前精确 RTL 的 Vivado 2023.2 | standalone 100 MHz WNS `+0.419 ns`；待提交后执行锁定的完整 SoC `perf20@100MHz` 构建 |

Vivado 独立 DRC 报告仍有无约束顶层 I/O 的 NSTD-1/UCIO-1 critical warning；这是未提供板级 XDC 的 standalone 综合，不是 RTL elaboration 或 synthesis error。在 standalone 100 MHz（10 ns）时钟约束下，所有时序约束已经满足：WNS `+0.419 ns`，TNS `0 ns`，失败端点为 0。该结果不含官方 SoC、板级 XDC、placement 和 routing，不能据此声称完整设计已经在板上闭合 100 MHz。最新已提交版本 `bd4fb1b` 的 100 MHz 完整 SoC implementation 已生成 bitstream 且 DRC 0 error，但 WNS/TNS 为 `-0.413678/-71.815697 ns`，所以它不是时序闭合基线。当前 cache 边界候选尚未产生完整 SoC routed DCP。

完整顶层 lint 有 853 条审计项，类别只有 `UNUSEDSIGNAL` 和 `CMPCONST`，精确签名为 `5c7dc1c4b5d8261b216d5a2222fef205d17d133ad9175ad18efc188e3985e836`。大部分来自统一 uop/commit/cache/translation Bundle 在具体路径中只消费部分字段、综合时关闭的 DiffTest 状态输入，以及官方 debug/兼容端口必须保留。Vivado 在综合时会裁剪这些字段，保留的窄状态读端口仍用于 `valid/requestSent/translationDone` 等易变控制。它们不是“以后会用”的功能预留；能在 Scala 结构层安全删除的字段应继续删除，但跨模块固定 Bundle 中的未消费字段由生成器保留更清晰。`reference/core-top-lint-waivers.json` 同时锁定 RTL SHA-256、warning 数量、类别和签名哈希，先运行无抑制审计，再只对完全匹配的签名执行 clean closure。它不是允许新增 warning 的全局开关。

综合资源（`xc7a200tfbg676-2`，flatten hierarchy rebuilt）：72,270 LUT、39,591 FF、58 RAMB36、16 RAMB18、4 DSP。其中 ROB 为 28,143 LUT / 5,719 FF，LSQ 为 2,064 LUT / 2,212 FF，四个 IQ 合计 6,074 LUT / 7,326 FF。IQ 以年龄顺序紧凑保存八项，唤醒标签直接比较 resident entry，oldest-ready 后只做一次 payload 索引；中间项发射时搬移所有年轻项，并把同拍 wake 合入搬移后的 ready bit。ROB payload 使用同步 bank 预取，retirement hot control 与大 payload 分离。ALU 和固定延迟 MUL 使用窄 tag 提前唤醒，MUL 数据在 PRF operand 边界转发；可变延迟 DIV 只经 ROB 寄存写回唤醒，避免 raw divider tag 直接进入 IQ oldest-ready 选择。Store 地址进入 LSU IQ，Store 数据进入独立 8-entry queue，二者按 ROB/STQ identity 在 LSQ 汇合。LSQ 选择 load 时同时寄存不可变 payload，后续翻译、store-order 和 forwarding 不再第二次经过宽 `loads(loadHead)` 选择；AGU 同拍旁路避免增加正常 load 延迟。当前 standalone 100 MHz WNS/TNS/失败端点为 `+0.419 ns / 0 ns / 0`。最终 8 线程综合证据的 `timing.rpt` SHA-256 为 `21613addd95db9d9a5ad22488086f1a87df8f785af0a2514fa3760be57730873`，`utilization.rpt` SHA-256 为 `7bec06769440c7dc4ff1675d7d0d0495dfe2d92750a6dc18feb03b19b287dd72`，DRC SHA-256 为 `c38c476060bc58abaea5233710797340f4eedd6d5979a8e3a12737a541802257`，DCP SHA-256 为 `1e690414cd8242dbd08cf9e92df77684f47278bbc13f9850da97b84264fda737`。

已提交的 LSQ 时序版本 `7ada9ba51e7e69b5e6c95a45dcf1984a4114a022` 完成了官方完整 SoC implementation：100 MHz WNS `-0.535200 ns`、TNS `-95.344513 ns`、90,110 slice LUT、55,281 registers、DRC 0 error、bitstream 成功。它比 banked MSHR 提交 `40a3b53` 的 `-0.977163/-1228.851318 ns` 继续改善，但仍未闭合。最差 CPU 路径变为 `recoveryEpoch_reg[1]` 经 ROB wakeup 和 IQ oldest-ready 选择到 `issueAddressUop_1.decoded.immediate`，10.386 ns 数据路径中 84.5% 为布线。锁定 package SHA-256 为 `a02b2b72ba0d3ab53a4cc80f6a1baf6d2328684b2796e467b45329572070101b`，包内全部 artifact 哈希已逐项验证。远端 `func58` Job `20260725-210149-13a43932` 仍在 programming 阶段因实验箱 `There is no current hw_target` 结束为 `infra_error`，没有 programming/VIO/DUT 结论。

registered epoch 提交 `2c376d740de384a9cee177d6831bf73802704ac4` 也完成了锁定的 100 MHz SoC implementation 和 bitstream：WNS `-0.562604 ns`、TNS `-263.107880 ns`、90,163 slice LUT、55,316 registers、56.5 BRAM、8 DSP、DRC 0 error。原 recovery-epoch/IQ 路径已经移出最差路径，但 WNS 比 `7ada9ba` 退化 0.027404 ns，TNS 明显变差，因此仍不是时序闭合。新的最差 CPU 路径从 LSQ `loadHead` 经 store-order/forwarding 和 completion 仲裁到 `completion.sideEffectData` 条件清零，数据延迟 10.029 ns、14 级逻辑，其中 7.381 ns（73.6%）为布线。对应 `.fpgajob` SHA-256 为 `cd78329d84a7c5812f881eb768f1adb27560cabf9d761f88ded6e280ffdc1491`，包内 8 个 artifact 均逐项通过 SHA-256 校验。本轮 LSQ payload 隔离正针对该路径，完整 SoC 结果仍待基于本次新提交生成。

宽后端提交 `fbe01256b376ecfd3367002b16e82d0f35900005` 的锁定 100 MHz `func58` 完整实现也成功生成 bitstream 且 DRC 0 error，但 WNS `-0.780680 ns`、TNS `-393.443848 ns`，仍未闭合。最差路径从执行簇 divider 的 `uop_pdst` 寄存器出发，经除法完成仲裁、同拍 IQ 唤醒和 oldest-ready 选择到 IQ payload 寄存器；10.319 ns 数据延迟中布线占 8.272 ns（80.2%）。该包远端 `func58` 通过，只能证明本次板测功能，不能覆盖负 WNS 风险。本轮候选据此将 variable-latency DIV 唤醒移到 ROB 寄存写回边界，并为同 lane 的 registered/direct wake 冲突加入老者优先仲裁。

DIV 寄存唤醒提交 `2965219e09a823244284ddc26b9fd77b382d0b9f` 的锁定 100 MHz 完整实现同样完成 bitstream 且 DRC 0 error，WNS 改善为 `-0.729440 ns`、TNS 改善为 `-183.101868 ns`，hold WNS 为 `+0.015 ns`。原 divider raw completion 路径已消失；最差路径改为 ROB `stagedPdst` 经物理槽位 IQ 的 age-to-slot 选择到 LSU payload。本轮紧凑年龄顺序 IQ 正是针对该结构路径，完整 SoC 结果必须由当前候选的精确提交重新生成。

旧文档中的 776,232 周期记录复用了早于 RTL 的 `obj_dir/Vsimu_top__ALL.a`，没有重新执行 Verilator 编译，因此不能作为真实性能证据。本轮固定流程中显式删除 `obj_dir/output` 并执行 `make -j8 verilator`。在完全相同的 DiffTest、TLBFILL 修复和 seed `5570815` 下，关闭静态预测的公平基线为 126,157 instructions / 783,358 clocks / IPC 0.161046；启用静态预测为 131,198 instructions / 744,827 clocks / IPC 0.176146；加入恢复训练表后为 131,226 instructions / 743,893 clocks / IPC 0.176404；允许数据侧 direct/DMW 翻译提前完成后为 131,225 instructions / 737,817 clocks / IPC 0.177856；让下一顺序取指组的地址翻译与当前 I-cache 请求重叠后为 130,008 instructions / 691,685 clocks / IPC 0.187958；让 instruction direct/DMW 翻译在请求接受拍直接产生寄存响应后为 132,934 instructions / 657,341 clocks / IPC 0.202230；让 L2 demand refill beat 在写入 L2 的同时流式返回请求 L1 后为 132,916 instructions / 599,313 clocks / IPC 0.221781；让 L1I 在请求所在 16B 组 refill 完成时提前返回为 132,917 instructions / 586,915 clocks / IPC 0.226467；提交 `f395204` 的跨组流式取指结果为 539,497 clocks；同步 banked predictor、响应预解码、FixBranch 和 refill replay 组合为 139,654 instructions / 538,742 clocks / IPC 0.259222；当前 banked MSHR 候选为 139,654 instructions / 538,555 clocks / IPC 0.259312，比提交基线减少 187 周期（0.0347%）。各次功能通过均由 NEMU DiffTest、`END by Syscall` 和 end PC 共同判定。

## 源码布局

```text
spinal/src/main/scala/openla500/
  compat/       官方 core_top 适配、AXI3 扁平化和发布生成器
  core/         OooCoreConfig、OooCore、OooCoreSystem、生成入口
  frontend/     取指、4-slot 到 3-uop 解码适配、LA32R decoder
  backend/      RAT/free-list/PRF、ROB、IQ、dispatch、LSQ、执行接线和提交
  execute/      四个执行端口的 ALU/branch/mul/div/AGU 集群
  memory/       L1I、L1D、共享 L2、MSHR、cache array、64B line AXI bridge
  predict/      四银行同步 BTB/PHT、GHR/RAS 和取指响应预解码
  privileged/   CSR 外部连接所需的地址翻译、TLB 管理和 IDLE 控制
  observe/      Chiplab commit/DPI 适配以及架构状态合同
  config/       仍被独立 leaf 合同测试使用的历史配置类型
```

测试目录与主代码一一对应：`spinal/src/test/scala/openla500/{core,frontend,backend,execute,memory,privileged,observe}`。新增 OoO 文件应放入职责对应的目录和 package，不要重新创建 flat `openla500.ooo` 目录。

## 固定微架构配置

配置入口是 `openla500.core.OooCoreConfig.FourIssueThreeCommit`。当前实现故意固定宽度，避免保留一套未验证的“可任意改宽度”逻辑：

| 结构 | 配置 |
| --- | --- |
| Fetch / decode / rename / dispatch | 4 / 3 / 3 / 3 |
| Execution issue / writeback / commit | 4 / 5 / 3 |
| Physical registers / ROB | 64 / 32 |
| Instruction buffer / dispatch queue | 8 / 8 |
| Per-port IQ / LDQ / STQ | 8 / 8 / 8 |
| Store-data queue | 8 |
| MSHR | 4 |
| L1I / L1D | 2-way，64 sets，64B line，8 KiB each |
| Shared L2 | 2-way，512 sets，64B line，64 KiB |
| Reset vector | `0x1c000000` |
| TLB | 32 entries，官方 `TLBNUM=32` |

四个执行端口的能力分别是：`alu-csr`（ALU/CSR/serial）、`alu-div`（ALU/div）、`alu-branch-mul`（ALU/branch/mul）、`load-store`（唯一 LSU）。第五条写回通道用于流水化乘法等 completion，提交仍严格限制为 ROB 顺序三条。

## 数据流和精确性

```text
L1I/translation -> OooFrontend(fetch4) -> OooDecodeRenameBuffer
                                      -> rename3/RAT/free-list/PRF/ROB
                                      -> DispatchQueue -> 4 x IssueQueue
                                      -> 4 x execution issue -> 5 x completion/WB
                                      -> ROB ordered commit3 -> architectural mirror/DPI
                                                            \
                                                             -> CSR/TLB/AXI/cache side effects
```

* 前端以 64B cache line 为填充单位，每个请求向解码侧提供四条 32-bit 指令；当前组等待 I-cache 响应时，翻译端可以预先处理下一个对齐 16B 顺序组，并缓存翻译结果或异常。direct/DMW instruction 请求在接受拍直接寄存物理地址、MAT 和 ADEF 元数据，只有分页请求进入 TLB pending。`OooBankedFetchPredictor` 按四个 fetch lane 分银行，每银行含 128-entry 同步 BTB、1024-entry 2-bit PHT，并共享 8-bit GHR 和 8-entry speculative/architectural RAS。条件分支在方向尚未完成提交训练时使用 BTFNT；提交边界训练精确方向、目标和 RAS，响应级 cold learning 只补一条确定的 direct branch。L1I/uncached AXI 在寄存响应旁生成 `OooFetchPredecode`，前端不再把 opcode 译码放在响应到状态更新的组合路径上。FixBranch 在响应拍比较提前预测与实际预解码：错误的 cached handoff 被阻止，已接受且不可取消的 uncached 请求由 `cacheDropPending` 排空，旧响应不能冒充纠正目标。预测结果随 fetch slot 入队，decode 不会因表更新而重算；分支 completion 恢复仍统一 flush frontend、rename buffer、IQ、ROB younger entries 和 LSQ。
* rename 同时分配 physical destination、ROB pointer、LDQ/STQ index。只有 `writesGpr && rd != 0` 的 uop 才携带 FreeList 给出的 `pdst`；写 `r0` 或无 GPR 目的的 uop 固定使用 `pdst=0`，不能误唤醒随后分配同一自由表标签的真实生产者。RAT 是投机映射，commit 时更新 architectural mapping 并释放旧 physical register；FreeList 使用 ysyx 风格的 `head/architecturalHead/tail` 环形队列，flush 只回退 speculative head 和 free count，commit 不会在 flush 边界写入回收槽位。
* 四个 IQ 分别按执行端口能力保存八项，并像 ysyx 一样保持 resident uop 按年龄紧凑排列；ready bitmap 因而天然按年龄排序，PriorityEncoder 后只需一次 payload 索引。发射中间项时年轻 payload 向 head 搬移，同拍 wake bit 合入搬移目标，避免脉冲丢失。serial/CSR/TLB/CACOP/IDLE 等操作必须等 ROB head，不能因为执行端空闲而越过更老指令。单周期 ALU 和固定延迟 MUL 可在结果进入通用 completion 仲裁前用窄 `valid/pdst` 唤醒依赖者；数据仍只在 PRF operand 边界转发，不把 32-bit 结果送入 IQ oldest-ready 选择网络。
* 分支在执行端比较实际 taken/target。错误预测 completion 生成 `OooRecoveryRequest`，目标 PC 和异常元数据一起保存，避免把普通 serial stall 当作 branch recovery。
* load 必须保留 ROB/LDQ 顺序、size/sign-extension 和目标 pdst。LSQ 的 cache request 输出有一拍寄存缓冲，flush 时丢弃未发出的 speculative load；已接受的 load 不再阻塞后续独立 load 发射，cache response 用完整 ROB generation pointer 在全部 8 个 LDQ entry 中匹配，不依赖当前 `loadHead`。Store 地址只等待 base operand 后即可进入 AGU/翻译，Store 数据由独立 8-entry `OooStoreDataQueue` 等待 `psrc2` 并写入同一 STQ entry；地址与数据都到齐后 ROB 才允许普通 Store 完成，异常或失败 SC 走精确例外。只有 ordered commit 后才允许对 cache/uncached 总线产生写副作用。无副作用的 direct/DMW 数据地址翻译可以与未解析的老 store 地址并行，真正的 D-cache 请求仍等待 store-order/forwarding 检查完成。
* LSQ 用退休同步的 `loadBase` 旋转 pending bitmap，并在其后寄存调度槽位和不可变 load payload；首次分配组只用 ROB age 初始化 base。`robPointer/recoveryEpoch/pdst/virtualAddress/size/byteMask/signExtend/isLl` 在选择边界一次性寄存，后续 forwarding 和 completion 不再通过第二个宽 `loads(loadHead)` mux；`valid/addressReady/requestSent/completed/translationDone/physicalAddress/uncached` 等易变状态仍从被选槽位读取。AGU 与 scheduler 同拍命中同一 load 时直接旁路新地址和元数据，故正常地址到翻译路径不增加周期。调度 mask 排除 `requestSent` entry，但不等待更老请求返回；老 store 未解析、部分覆盖和 forwarding 规则仍可阻止不安全的年轻 load。cache load response 不能反压，因此它与 store completion 同拍时由 load 占用 completion 端口，store 保持 pending 并在下一拍重试，只有实际发出 store completion 后才置 `completed`。
* ROB 在 completion 到达拍完成 valid、generation pointer 和未完成状态检查，并寄存 accepted one-hot 目标以及 result、pdst、writesPdst、side-effect、exception、branch payload。下一拍同一个 stage 一方面写入 ROB entry/开放 commit，另一方面直接向 IQ、PRF 和 ready-map 提供物理写回，不再经过后端第二套 completion 寄存器；依赖唤醒和 PRF 写入的周期没有增加。commit payload 按三提交 lane 进行同步 bank 预取，valid/complete/exception/serial 等 hot control 保留窄寄存状态，避免 182-bit entry 异步 mux 落在退休和 predictor 更新路径。flush 会屏蔽 staged wakeup 并清空 one-hot，重复或 stale completion 不会写入已经复用的 entry。
* ROB 以 program order 提交最多三条。异常、ERTN、CSR、TLB、cache operation 和 barrier 都在 head 处理；外部 `OooCoreSystem` 在该边界接管 eentry/tlbrentry/ERA 和 CSR 更新，保证 precise exception。
* Chiplab 多提交适配按 lane 输出 instruction/load/store 事件，但异常、CSR 和架构状态是单一全局流。DPI 适配不是提交逻辑的旁路，不能用 debug 端口替代内部 commit。

## 内部接口合同

### `OooCore`

`openla500.core.OooCore` 是不含 CSR/TLB/AXI 外壳的自取指核心。主要边界如下：

| 方向 | 接口 | 语义 |
| --- | --- | --- |
| master/slave Stream | `instructionTranslationRequest/Response` | 前端虚拟地址到物理地址、MAT、异常元数据 |
| master/slave Stream | `dataTranslationRequest/Response` | LSU 地址翻译，带 ROB pointer/pdst 上下文 |
| out/in | `memoryRead*`、`memoryWrite*` | 64B line 读写及 8 个 64-bit beat |
| out/in | `uncachedInstruction*`、`uncachedData*` | 设备/禁 cache 访问，保留请求上下文 |
| in/out | `systemRead*`、`csrWrite*`、`exception*` | ROB head 的系统状态和精确异常边界 |
| out | `commit[3]`、`commitValid`、`recovery` | 有序提交和恢复请求 |
| in | `externalRedirect*`、cache invalidate、reservation | ERTN/IDLE/维护操作和 LL/SC 环境 |

### `OooCoreSystem` / 官方 top

`OooCoreSystem` 在同一 `aclk`/同步高有效 `reset` 域内实例化 CSR、32-entry TLB 地址翻译、IDLE 控制器和 `OooAxiLineBridge`，并维护 commit 时更新的 32 个架构 GPR 镜像。CSR、ERTN、TLB、cache maintenance 和 LL/SC reservation 的状态变更 payload 在提交边界寄存一拍，并在现有 privileged redirect/flush 到达的时钟沿应用；TLBFILL 的随机替换索引与有效脉冲同拍捕获，避免副作用延迟时使用下一拍的计时器低位。redirect 产生时序没有额外增加一拍。这一边界只切断组合控制路径，不改变精确异常或指令可见顺序。

官方 `core_top` 仍严格保持 49 个端口和历史 AXI3/WID 方向：

| 分组 | 端口 |
| --- | --- |
| clock/reset/interrupt | input `aclk`, `aresetn`（低有效），`intrpt[7:0]` |
| AXI read address | output `arid[3:0]`, `araddr[31:0]`, `arlen[7:0]`, `arsize[2:0]`, `arburst[1:0]`, `arlock[1:0]`, `arcache[3:0]`, `arprot[2:0]`, `arvalid`; input `arready` |
| AXI read data | input `rid[3:0]`, `rdata[31:0]`, `rresp[1:0]`, `rlast`, `rvalid`; output `rready` |
| AXI write address | output `awid[3:0]`, `awaddr[31:0]`, `awlen[7:0]`, `awsize[2:0]`, `awburst[1:0]`, `awlock[1:0]`, `awcache[3:0]`, `awprot[2:0]`, `awvalid`; input `awready` |
| AXI write data/response | output `wid[3:0]`, `wdata[31:0]`, `wstrb[3:0]`, `wlast`, `wvalid`; input `wready`, `bid[3:0]`, `bresp[1:0]`, `bvalid`; output `bready` |
| debug | input `break_point`, `infor_flag`, `reg_num[4:0]`; output `ws_valid`, `rf_rdata[31:0]`, `debug0_wb_pc[31:0]`, `debug0_wb_rf_wen[3:0]`, `debug0_wb_rf_wnum[4:0]`, `debug0_wb_rf_wdata[31:0]`, `debug0_wb_inst[31:0]` |

顶层 `arlen/awlen` 之所以是 8 bit 是官方合同要求，内部 bridge 只生成合法 burst 长度。`debug0_wb_inst` 即使 SoC 当前未接线也必须保留。

复位捕获由 compatibility wrapper 完成：上电先保持后端 reset，直到采样到一次 `aresetn=0`；之后沿用原同步复位时序。发布 gate 会把 `TLBNUM != 32` 合并到 reset capture，非法参数只会保持复位，不会产生未验证的 TLB 配置。

### Cache/AXI line 边界

`OooCacheContract` 固定 `LineBytes=64`、`BeatBytes=8`、每行 8 个内部 beat。`OooLineReadRequest` 携带 line address、MSHR ID 和 3-bit `criticalBeat`。L1I/L1D 共享 `OooSharedCacheHierarchy` 的 L2 和 `OooSharedReadMshrRouter`。router 是 4 个全局 line-read ID 的唯一所有者，记录 instruction/data owner 和 client local ID，并原样下传 critical beat；未知返回 ID 不会被转发。L1I 当前仍只有一个 local miss context，但能与多个 L1D/L2 miss 并存。

L1D 有 4 个实际 MSHR 和 8 个 load waiter。同 line load/store 合并，同 set 不同 line 保守串行，其他 set 和 cache hit 可在 miss 下继续。每个 MSHR 保存地址、critical beat、victim 元数据、refill mask/error 和 waiter 状态；8 个浅层 64-bit bank 保存四条在途 line 的 refill beat，避免每个 MSHR 复制完整 512-bit line 寄存器。waiter 的目标 beat 一到达即可返回 load，MSHR 仍继续收齐其余 beat 并安装整行。dirty victim 使用一个全局缓冲并串行写回；merged store 进入单项 pending-store 缓冲，应用时更新对应 bank 和 byte mask。最后一个 refill beat 与 pending store 的竞争会延迟 install，确保 store byte 优先。

L2 以恢复后的全局 ID 直接索引 4 个 MSHR，支持不同 set 并行、hit-under-miss 和任意 ID 交错的 refill；8 个浅层 beat bank 保存四条 refill line，单项 dirty victim 缓冲负责写回。外部 refill beat 在写入 L2 bank 的同拍捕获进一项弹性输出寄存器；首次输出增加一拍，但下游消费同拍可以接收下一 beat，持续吞吐仍为一 beat/cycle。命中数据先进入 registered hit-capture，再顺序写入 bank 并由单项输出寄存器返回。该边界切断 AXI/L2 状态到 L1I predecode 的组合路径，但当前 `func_lab19` 从 534,497 增至 552,247 clocks，完整 SoC 时序若不能因此闭合就应撤销或改为更窄的 I-side 隔离。L1I 在请求 16B group 就绪时先返回，并用 `refillReplayPending` 把同线已就绪 group 的响应延后一拍，切断 response-to-response/predecode 时序环。

`OooAxiLineBridge` 把 cached read 映射到 AXI ID 4..7，每个 ID 分别保存 active、32-bit half、error、beat index 和返回计数，因此最多保留 4 个已发 AR 的 64B burst，并接受交错 R 返回。数据侧 miss 使用 16 个 32-bit transfer 的 WRAP burst，从 `criticalBeat * 8` 开始并在 64B 边界回绕；`last` 由独立 8-beat 计数器判定，不能错误地把地址 beat 7 当作固定末拍。I 侧 `criticalBeat` 当前固定为 0：A/B 测试表明 I-side critical-first 会把 `func_lab19` 从 533,744 退化到 536,336 cycles，因此未保留。高 32-bit half 只在 64-bit 输出寄存器为空时接收，切断 cache backpressure 到 AXI `rready` 的组合路径；正常 low/high 序列仍可每拍接收一个 32-bit word。IDs 2/3 分别保留给 uncached instruction/data read。line write 和 uncached traffic 仍全局有序，data 访问保留 size、byte mask 和 write response backpressure。

### Privileged/maintenance

`OooAddressTranslationUnit` 支持 direct、DMW、分页 TLB hit、refill/invalid 异常，并将 TLB search/read/write/fill/invalidate 作为 ROB head side effect。数据侧和指令侧的 direct/DMW 请求都直接寄存物理地址、cache 属性与对齐异常，分页请求仍走 TLB pending 路径；CSR 翻译上下文在精确 refetch 边界更新，不会让新特权状态提前可见。`CACOP`、`PRELD`、`DBAR`、`IBAR`、LL/SC 和 IDLE 不得绕过 LSQ/ROB 的顺序边界；cache invalidate 信号在 `OooCoreSystem` 映射到 L1I、L1D、writeback-invalidate 和 L2 四类维护动作。

## 生成、检查和官方仿真

推荐从仓库根目录运行：

```bash
# WSL/Linux，生成原始 RTL、打包官方顶层并创建忽略的 rtl/ 镜像
make generate-core
make port-check
make lint
make yosys-check
make publish-check

# Scala 全量测试
make scala
make test

# Python 仓库门禁
make python-test
```

等价的生成类名已按源码 package 分类：

```text
openla500.compat.GenerateCoreTopCompat
openla500.core.GenerateOooCore
openla500.core.GenerateOooCoreSystem
openla500.backend.GenerateOooBackend
openla500.backend.GenerateOooBackendWithDataCache
openla500.memory.GenerateOooDataCacheHierarchy
openla500.memory.GenerateOooSharedCacheHierarchy
```

官方 chiplab 验证需要 Linux 文件系统和 `CHIPLAB_HOME`：

```bash
export CHIPLAB_HOME=/home/ubuntu/nscscc-validation/ooo-manual-20260720
cp rtl/mycpu_top.v "$CHIPLAB_HOME/IP/myCPU/mycpu_top.v"
cd "$CHIPLAB_HOME/sims/verilator/run_prog"
./configure.sh --run func/func_lab19 --disable-simu-trace --output-uart-info
rm -rf obj_dir output
make -j8 verilator
make testbench
make soft_compile
make simulation_run_prog TIME_LIMIT=1300000
```

必须在 `make verilator` 和 `make testbench` 之前运行 `configure.sh`，否则编译参数仍是上一次配置；不能省略 `make verilator`，否则可能复用旧的 `obj_dir/Vsimu_top__ALL.a`。清理 `obj/` 后必须重新运行 `make soft_compile`，否则缺少 `rom.vlog` 的仿真会在初始化阶段退出。当前基线保留默认 `TRACE_COMP=y` 以获得正常结束条件；验证目录没有 `golden_trace.txt` 时复制会报警，但 NEMU DPI DiffTest 仍然执行，最终以 DiffTest、syscall 和 end PC 三项共同判断。不要使用会让当前测试失去结束条件的 `--disable-trace-comp --disable-simu-trace` 组合。

Vivado standalone 综合（PowerShell）：

```powershell
& 'D:\Xilinx\Vivado\2023.2\bin\vivado.bat' -mode batch `
  -source tools/ooo_core_top_synth.tcl `
  -tclargs (Resolve-Path 'rtl/mycpu_top.v').Path (Join-Path (Resolve-Path '.').Path 'build/vivado/core_top')
```

## 交接时的约束

1. 只在 `spinal/src/main/scala` 中实现 CPU 逻辑；`build/core_top/package/rtl/mycpu_top.v` 和被 Git 跟踪的 `rtl/mycpu_top.v` 发布镜像必须由 `make generate-core` 产生，并通过 replacement spec 的 SHA-256 检查，不能手工编辑。
2. 新的 OoO 模块按上述功能目录放置；测试 package 必须与主 package 一致。不要重新引入 `openla500.ooo` 或 `openla500.pipeline` flat namespace。
3. 任何宽度/队列/line geometry 改动都必须同时更新 `OooCoreConfig` 的 require、对应 directed test、官方仿真和 Vivado 资源/时序记录；不能只改生成参数。
4. 先验证功能，再看时序。当前 standalone 100 MHz WNS 为正；不能用综合约束屏蔽真实路径，也不能把 standalone synthesis 扩大为 complete-SoC timing closure。远程评测直接使用 `perf20`，只有 `perf20` 暴露功能问题时才回到 `func58`；三次真实测试尚未执行，不能把本地仿真收益当作 FPGA 性能结论。
5. 官方 `func_lab19` 通过不等于 full random、Linux、FPGA 或比赛性能全部通过。每轮性能结论要记录实际 workload、时钟、seed、commit 和报告哈希。
6. 当前候选已通过功能、端口、Yosys、synthesis 和 standalone 100 MHz timing；下一轮性能或时序修改必须重新跑 Scala 全量测试、官方 DiffTest 和 Vivado，而不是只比较 RTL 文本。当前候选的官方计数为 552,247 clocks，standalone Vivado WNS 为 `+0.419 ns`。Vivado 主机策略固定为 `general.maxThreads=8`，没有显式设置并发数的 `launch_runs` 默认使用 `-jobs 4`。

## 优化试验记录

以下记录使用同一个官方 `func_lab19`、NEMU DiffTest 和 100 MHz standalone Vivado 口径。候选未同时满足功能、性能和时序时不得作为新基线。

| 候选 | `func_lab19` | standalone WNS | 结论 |
|---|---:|---:|---|
| L1I BRAM 命中结果直接送前端 | 536,350 cycles，`END by Syscall` | `-3.343 ns` | 周期比 `f395204` 的 539,497 少 0.583%，但 BRAM tag/hit 到分支译码和前端状态形成 18 级组合路径，放弃 |
| 128 项异步、2-bit、提交训练的方向预测表 | 536,483 cycles，`END by Syscall` | `-3.275 ns` | 误预测约减少 5%，但 128 项异步读取形成大 mux；后续预测器必须改为提前索引的 banked 同步 BRAM，不能继续扩大响应级表 |
| 注册式 L1I 响应加两项有序请求跟踪，8 项指令缓冲 | 551,227 cycles，`END by Syscall` | 未综合 | 比 `f395204` 慢 2.174%，前端空周期增加，放弃 |
| 上述请求跟踪加 16 项指令缓冲 | 551,017 cycles，`END by Syscall` | 未综合 | 只比 8 项版本减少 210 cycles，仍比 `f395204` 慢 2.135%；容量不是主因，放弃 |
| 仅将基线指令缓冲从 8 项扩为 16 项 | 539,497 cycles，`END by Syscall` | 未综合 | 与 `f395204` 逐周期相同，只增加存储和指针成本，放弃 |
| 32 项双组合查询提前目标表 | 538,501 cycles，`END by Syscall` | `-2.658 ns` | 周期改善 0.185%，但 tag 到 `nextFetchPc` CE 为 12.313 ns、23 级逻辑，且增加约 2,421 LUT/1,888 FF；必须改为同步 banked 预测，放弃 |
| 四银行同步 BTB/PHT、响应预解码、FixBranch 和 refill replay | 538,742 cycles，`END by Syscall` | `+0.135 ns` | 相对 `f395204` 减少 755 cycles；本地功能和 100 MHz 时序通过，进入远程 `func58/perf20` 候选 |
| 4-entry L1D/L2 MSHR、8 load waiter、4 AXI cached ID、banked refill/store buffer | 538,555 cycles，`END by Syscall` | `+0.137 ns` | 比提交基线减少 187 cycles；本地 110/110、DiffTest 和 standalone 时序通过，完整 SoC/真实 `perf20` 尚待验证 |
| LSQ 地址不对齐异常完成缓冲 | 538,555 cycles，`END by Syscall` | `+0.359 ns` | 普通 AGU ready 与 load/translation completion 仲裁解耦；本地 111/111、DiffTest 和 standalone 时序通过，周期不变，完整 SoC 尚待验证 |
| ROB completion epoch 同拍寄存 | 538,555 cycles，`END by Syscall` | `+0.292 ns` | 隔离 currentEpoch 到 IQ oldest-ready 长路径；本地 112/112、DiffTest 和 standalone 时序通过，周期不变，完整 SoC 尚待验证 |
| LSQ completion payload/valid 解耦 | 538,555 cycles，`END by Syscall` | `+0.292 ns` | payload 每拍采样且 LL sidecar 独立生成，切断 forwarding 到 32-bit 条件清零；本地 112/112、362/362、DiffTest 和 standalone 时序通过，完整 SoC 尚待验证 |
| ROB 同步提交 bank、ALU/MUL 提前唤醒、Store 地址/数据解耦 | 533,744 cycles，`END by Syscall` | `+0.359 ns` | 相对 `d126f57` 减少 4,811 cycles（0.893%），并把 standalone 资源降至 71,070 LUT / 39,450 FF；本地 124/124、362/362 和 DiffTest 通过 |
| I-side AXI critical-first refill | 536,336 cycles，`END by Syscall` | 未单独综合 | 相对当前候选退化 2,592 cycles（0.486%），关闭；D-side critical-first 单独启用仍为 533,744 cycles |
| DIV raw completion 唤醒寄存化、registered wake 同 lane 优先 | 534,497 cycles，`END by Syscall` | `+0.359 ns` | 消除已知 divider-to-IQ 结构路径；相对 `fbe0125` 增加 753 cycles（0.141%），本地 125/125、362/362 和 DiffTest 通过，完整 SoC route 决定是否保留 |
| 紧凑年龄顺序 IQ | 534,497 cycles，`END by Syscall` | `+0.359 ns` | 直接 tag compare、年龄选择后一次 payload 索引；物理槽位中间版为 `-0.044 ns`，紧凑版修复 `0.403 ns`，代价为 +999 LUT/-121 FF；本地 126/126、362/362 和 DiffTest 通过；完整 SoC WNS `-0.584979 ns` |
| LSQ 已选 load payload 寄存及 completion 冲突修复 | 按新策略待真实 `perf20` | 前一生成版本 `+0.359 ns` | 宽不可变 payload 在选择边界寄存，AGU 同拍旁路保持延迟；load response/store completion 冲突时 store 下一拍重试；本地 127/127、362/362、完整 SoC bitcount PASS |
| L2 write priority、弹性 refill 输出与延迟 cached FixBranch kill | 552,247 cycles，`END by Syscall` | `+0.419 ns` | 本地 130/130、362/362 和 DiffTest 通过；比 534,497 clocks 退化 3.32%，只有完整 SoC 100 MHz route 闭合才值得保留 |

这些试验说明：响应级异步大表或单纯扩容会用很大的面积/时序代价换取很小的周期收益；同步 banked 状态、按固定/可变延迟分类的窄 tag 唤醒、紧凑 IQ 和真实并发 MSHR 才能保留寄存边界。ALU/MUL 提前唤醒和 Store 地址/数据解耦已经实现，L1D 也能在目标 beat 到达时提前返回。下一决定性门禁是当前 cache 边界候选的 100 MHz SoC placement/routing：若 WNS 非负，再做三次真实 `perf20`；若仍为负，则以 routed top paths 设计更窄的寄存边界，避免接受 3.32% 周期退化。WNS 是否非负与板测是否通过必须分别报告，在结果出来前不能把正 standalone WNS 或负 WNS 下的板测通过描述为完整时序闭合。
