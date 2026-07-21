# 4 发射 / 3 提交乱序核交接说明

本文是当前 `dev-OoOE` 分支的单一架构和验证入口。代码由 Scala/SpinalHDL 生成，权威发布产物是 `build/core_top/package/rtl/mycpu_top.v`；被 Git 忽略的 `rtl/mycpu_top.v` 只是给 Chiplab、Vivado 和门禁使用的同内容镜像，不是手写 Verilog 的第二份实现。

## 状态与基线

当前官方顶层已经实例化 `openla500.core.OooCoreSystem(OooCoreConfig.FourIssueThreeCommit)`。旧 `SpinalCoreBackend` 和 `openla500.pipeline` 不再参与生成；保留下来的少量 `OpenLa500*` leaf 模块仅供仍被 OoO 核复用的 ALU、乘除法、CSR、TLB 或独立合同测试使用。

当前验证基线（2026-07-21，生成 RTL SHA-256 `a2e101af5760fa487a85d53331f13c877c94183f11b902dfac8fb917b78da71b`）如下：

| 检查 | 结果 |
| --- | --- |
| Scala/Spinal/Verilator | 35 suites，89 tests，89 passed，0 failed，0 aborted |
| Python repository gates | 362 tests，362 passed，0 failed/error |
| core_top package/port contract | pass，49 ports，17 inputs，32 outputs，`TLBNUM=32` |
| Verilator complete-top lint | pass，664 条精确签名审计后 closure 为 0 warning/error |
| Yosys 结构检查 | pass，Yosys 0.33，无 warning/skip |
| chiplab `func/func_lab19` + NEMU DiffTest | pass，syscall 结束并到达 end PC |
| 官方仿真计数 | 132,916 committed instructions，599,313 clocks，IPC 0.221781 |
| Vivado 2023.2 synthesis | 0 errors，0 critical synthesis warnings，DCP/report 生成成功 |

Vivado 独立 DRC 报告仍有无约束顶层 I/O 的 NSTD-1/UCIO-1 critical warning；这是未提供板级 XDC 的 standalone 综合，不是 RTL elaboration 或 synthesis error。在 standalone 100 MHz（10 ns）时钟约束下，所有时序约束已经满足：WNS `+0.419 ns`，TNS `0 ns`，失败端点为 0。当前最差路径仍是 backend issue operand 到 multiplier result。

完整顶层 lint 有 664 条审计项，类别只有 `UNUSEDSIGNAL` 和 1 条固定宽度 `CMPCONST`。大部分来自统一 uop/commit/cache/translation Bundle 在具体路径中只消费部分字段、综合时关闭的 DiffTest 状态输入，以及官方 debug/兼容端口必须保留。它们不是“以后会用”的功能预留；能在 Scala 结构层安全删除的字段应继续删除，但跨模块固定 Bundle 中的未消费字段由生成器保留更清晰。`reference/core-top-lint-waivers.json` 同时锁定 RTL SHA-256、warning 数量、类别和签名哈希，先运行无抑制审计，再只对完全匹配的签名执行 clean closure。它不是允许新增 warning 的全局开关。

综合资源（`xc7a200tfbg676-2`，flatten hierarchy rebuilt）：72,015 LUT、39,676 FF、42 RAMB36、12 RAMB18、4 DSP。最终 `timing.rpt` SHA-256 为 `07dee1f2e614d8b97d691c47c613bb4992d1e16b90108e3cb73d1f1d89d879c6`，`utilization.rpt` SHA-256 为 `ffc00e9a7f00d10d078d93073f639fbf96d0230a8a9bcd5015a3676b945f3ef4`。后续若继续提高频率，应优化乘法输入/结果路径；当前 100 MHz 已真实闭合，不需要也不允许用 false path 掩盖。

旧文档中的 776,232 周期记录复用了早于 RTL 的 `obj_dir/Vsimu_top__ALL.a`，没有重新执行 Verilator 编译，因此不能作为真实性能证据。本轮固定流程中显式执行 `make -j8 verilator`。在完全相同的 DiffTest、TLBFILL 修复和 seed `5570815` 下，关闭静态预测的公平基线为 126,157 instructions / 783,358 clocks / IPC 0.161046；启用静态预测为 131,198 instructions / 744,827 clocks / IPC 0.176146；加入恢复训练表后为 131,226 instructions / 743,893 clocks / IPC 0.176404；允许数据侧 direct/DMW 翻译提前完成后为 131,225 instructions / 737,817 clocks / IPC 0.177856；让下一顺序取指组的地址翻译与当前 I-cache 请求重叠后为 130,008 instructions / 691,685 clocks / IPC 0.187958；让 instruction direct/DMW 翻译在请求接受拍直接产生寄存响应后为 132,934 instructions / 657,341 clocks / IPC 0.202230；本轮让 L2 demand refill beat 在写入 L2 的同时流式返回请求 L1 后为 132,916 instructions / 599,313 clocks / IPC 0.221781。相对上一提交减少 58,028 周期（8.83%），相对关闭静态预测的公平基线减少 184,045 周期（23.49%）。各次都由 NEMU DiffTest、`END by Syscall` 和 end PC 共同判定通过。

## 源码布局

```text
spinal/src/main/scala/openla500/
  compat/       官方 core_top 适配、AXI3 扁平化和发布生成器
  core/         OooCoreConfig、OooCore、OooCoreSystem、生成入口
  frontend/     取指、4-slot 到 3-uop 解码适配、LA32R decoder
  backend/      RAT/free-list/PRF、ROB、IQ、dispatch、LSQ、执行接线和提交
  execute/      四个执行端口的 ALU/branch/mul/div/AGU 集群
  memory/       L1I、L1D、共享 L2、MSHR、cache array、64B line AXI bridge
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

* 前端以 64B cache line 为填充单位，每个请求向解码侧提供四条 32-bit 指令；当前组等待 I-cache 响应时，翻译端可以预先处理下一个对齐 16B 顺序组，并缓存翻译结果或异常。direct/DMW instruction 请求在接受拍直接寄存物理地址、MAT 和 ADEF 元数据，只有分页请求进入 TLB pending。预翻译不会越过未处理的 redirect，预测跳转会丢弃或 drain 错路径响应，向 L1I 真正发请求前还会重新检查四个 instruction-buffer 空位，避免旧响应填充后覆盖有效指令。静态预解码对 `B/BL` 直接预测跳转，并对向后条件分支采用 BTFNT。32-entry 带 tag 的恢复训练表只学习 ROB 已确认的方向/目标错误，用于覆盖反静态模式和 JIRL；预测结果随 fetch slot 入队，decode 不会因表更新而重算出不同结果。响应组在第一条预测跳转处截断并重定向。分支恢复由 `OooCore` 捕获 completion 后统一 flush frontend、rename buffer、IQ、ROB younger entries 和 LSQ。
* rename 同时分配 physical destination、ROB pointer、LDQ/STQ index。只有 `writesGpr && rd != 0` 的 uop 才携带 FreeList 给出的 `pdst`；写 `r0` 或无 GPR 目的的 uop 固定使用 `pdst=0`，不能误唤醒随后分配同一自由表标签的真实生产者。RAT 是投机映射，commit 时更新 architectural mapping 并释放旧 physical register；FreeList 使用 ysyx 风格的 `head/architecturalHead/tail` 环形队列，flush 只回退 speculative head 和 free count，commit 不会在 flush 边界写入回收槽位。
* IQ 按执行端口能力选择 ready uop；serial/CSR/TLB/CACOP/IDLE 等操作必须等 ROB head，不能因为执行端空闲而越过更老指令。
* 分支在执行端比较实际 taken/target。错误预测 completion 生成 `OooRecoveryRequest`，目标 PC 和异常元数据一起保存，避免把普通 serial stall 当作 branch recovery。
* load 必须保留 ROB/LDQ 顺序、size/sign-extension 和目标 pdst。LSQ 的 cache request 输出有一拍寄存缓冲，flush 时丢弃未发出的 speculative load；store 保持在 SQ，只有 ordered commit 后才允许对 cache/uncached 总线产生写副作用。无副作用的 direct/DMW 数据地址翻译可以与未解析的老 store 地址并行，真正的 D-cache 请求仍等待 store-order/forwarding 检查完成。
* LSQ 用退休同步的 `loadBase` 旋转 pending bitmap，并在其后寄存调度槽位；首次分配组只用 ROB age 初始化 base。这样既支持物理槽位绕回，又把选择网络与 ROB completion 写使能隔开，调度延迟增加一拍但稳态仍每拍可推进一个 LSU 请求。
* ROB 在 completion 到达拍完成 valid、generation pointer 和未完成状态检查，并寄存 accepted one-hot 目标以及 result、pdst、writesPdst、side-effect、exception、branch payload。下一拍同一个 stage 一方面写入 ROB entry/开放 commit，另一方面直接向 IQ、PRF 和 ready-map 提供物理写回，不再经过后端第二套 completion 寄存器；依赖唤醒和 PRF 写入的周期没有增加。flush 会屏蔽 staged wakeup 并清空 one-hot，重复或 stale completion 不会写入已经复用的 entry。
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

`OooCacheContract` 固定 `LineBytes=64`、`BeatBytes=8`、每行 8 个内部 beat。L1I/L1D 共享 `OooSharedCacheHierarchy` 的 L2 和 `OooSharedReadMshrRouter`，I/D miss 通过 4-entry MSHR 标识复用。L2 demand miss 接受的内存 beat 会在写入 refill buffer 的同拍流式返回请求 L1；下游 backpressure 同步作用于内存 beat ready，最后一拍之后再把完整 line 安装进 L2，不再收满后额外重放 8 拍。L2 hit 仍从已安装 line 顺序返回 8 拍。L1D 的 dirty victim 以 write-through 方式写入 L2 并保留为 clean L2 hit；L2 再通过 `OooAxiLineBridge` 拆成官方 32-bit AXI burst。未经 cache 的 instruction 访问使用对齐四字 burst，data 访问保留 size、byte mask 和 write response backpressure。

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
./configure.sh --run func/func_lab19 --disable-clk-time --dump-fst
make -j8 verilator
make -j8 testbench
rm -rf tmp
CHIPLAB_HOME=/home/ubuntu/nscscc-validation/ooo-manual-20260720 make simulation_run_prog
```

必须在 `make verilator` 和 `make testbench` 之前运行 `configure.sh`，否则编译参数仍是上一次配置；不能省略 `make verilator`，否则可能复用旧的 `obj_dir/Vsimu_top__ALL.a`。当前基线保留默认 `TRACE_COMP=y` 以获得正常结束条件；验证目录没有 `golden_trace.txt` 时复制会报警，但 NEMU DPI DiffTest 仍然执行，最终以 DiffTest、syscall 和 end PC 三项共同判断。不要使用会让当前测试失去结束条件的 `--disable-trace-comp --disable-simu-trace` 组合。

Vivado standalone 综合（PowerShell）：

```powershell
& 'D:\Xilinx\Vivado\2023.2\bin\vivado.bat' -mode batch `
  -source tools/ooo_core_top_synth.tcl `
  -tclargs (Resolve-Path 'rtl/mycpu_top.v').Path (Join-Path (Resolve-Path '.').Path 'build/vivado/core_top')
```

## 交接时的约束

1. 只修改 `spinal/src/main/scala` 中的源代码；`build/core_top/package/rtl/mycpu_top.v` 和忽略的 `rtl/mycpu_top.v` 镜像必须由 `make generate-core` 产生，并通过 replacement spec 的 SHA-256 检查，不能加入 Git 或手工编辑。
2. 新的 OoO 模块按上述功能目录放置；测试 package 必须与主 package 一致。不要重新引入 `openla500.ooo` 或 `openla500.pipeline` flat namespace。
3. 任何宽度/队列/line geometry 改动都必须同时更新 `OooCoreConfig` 的 require、对应 directed test、官方仿真和 Vivado 资源/时序记录；不能只改生成参数。
4. 先验证功能，再看时序。当前最紧路径是 issue operand -> multiplier result，100 MHz WNS 为正；不能用综合约束屏蔽真实路径。当前没有上板环境，上板数据不作为本轮门禁；环境恢复后再以三次真实测试的最低结果确认 FPGA 性能。
5. 官方 `func_lab19` 通过不等于 full random、Linux、FPGA 或比赛性能全部通过。每轮性能结论要记录实际 workload、时钟、seed、commit 和报告哈希。
6. 当前基线已通过功能、端口、Yosys、synthesis 和 standalone 100 MHz timing；下一轮性能或时序修改必须重新跑 Scala 89 项、官方 DiffTest 和 Vivado，而不是只比较 RTL 文本。当前基线的官方计数为 599,313 clocks，Vivado WNS 为 `+0.419 ns`。
