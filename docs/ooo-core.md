# 4 发射 / 3 提交乱序核交接说明

本文是 dev-OoOE 分支的架构、接口、验证和迁移入口。CPU 逻辑由 Scala/SpinalHDL 生成；权威生成物是 `build/core_top/package/rtl/mycpu_top.v`，Git 跟踪的 `rtl/mycpu_top.v` 是内容相同的发布镜像，不是第二份手写实现。

## 当前基线

官方顶层已经实例化 `openla500.core.OooCoreSystem(OooCoreConfig.FourIssueThreeCommit)`。旧的 `SpinalCoreBackend` 和 `openla500.pipeline` 不参与生成；仍存在的少量 `OpenLa500*` leaf 只供 OoO 核复用或独立合同测试使用。

精确状态以机器可读的 [refactor/status.yml](refactor/status.yml) 为唯一权威记录：

| 项目 | 当前结果 |
| --- | --- |
| RTL 基线提交 | `da71fd32e0db3d13f1964895bbafeb5d2e5af412` |
| 生成 RTL SHA-256 | `14874c00bf2a4632ac9792da2234286d4f1ac05140df03b7db90b784d00074f0` |
| 本地门禁 | Scala 37 suites / 133 passed；Python 362 passed；port、lint、Yosys、publish 全部通过 |
| standalone Vivado 100 MHz | WNS `+0.419 ns`，TNS `0 ns` |
| 完整 SoC 100 MHz | implementation 和 bitstream 完成；WNS `+0.036678 ns`，TNS `0 ns`，DRC 0 Error |
| 三次真实 perf20 | 全部 20/20；最低 `soc_count=74,446,699`，即 `0.74446699 s` |
| 性能参考 | `724b808959957c27fc64bda36b8c5cb828f51c8b` 的最低 `73,826,502` cycles |
| 当前结论 | 功能正确且 100 MHz 时序闭合；比性能参考慢 0.84%，不是性能提升 |

三次板测使用同一个锁定包，SHA-256 为 `bfe51c269e939588698f1f1de52f73bfa74f0d34904c7cdaa594296e243f99fa`；Job ID 和逐项哈希验证状态记录在 status.yml。完整 SoC 的 setup 余量只有 0.036678 ns，因此任何 RTL 修改都必须重新走完整实现，不能沿用本次闭合结论。

顶层 lint 当前审计 849 条生成器 warning，类别只有 `CMPCONST` 和 `UNUSEDSIGNAL`。它们由 `reference/core-top-lint-waivers.json` 按 RTL 哈希和精确签名锁定，不是允许新增 warning 的通配豁免。仓库根目录的 `baseline.txt` 是最初标量核的历史比赛基准，不是当前 RTL 或当前性能参考。

## 源码布局

~~~text
spinal/src/main/scala/openla500/
  compat/       官方 core_top 适配、AXI3 扁平化、发布生成器
  core/         OooCoreConfig、OooCore、OooCoreSystem、生成入口
  frontend/     取指、4-slot 到 3-uop 适配、LA32R decoder
  backend/      RAT/free-list/PRF、ROB、IQ、dispatch、LSQ、提交
  execute/      ALU、branch、mul、div、AGU 执行簇
  memory/       L1I、L1D、共享 L2、MSHR、cache array、AXI bridge
  predict/      banked BTB/PHT、GHR/RAS、取指响应预解码
  privileged/   CSR 外部连接、地址翻译、TLB、IDLE
  observe/      Chiplab commit/DPI 适配、架构状态合同
  config/       仍被独立 leaf 合同测试使用的历史配置类型
~~~

对应测试位于 `spinal/src/test/scala/openla500/{core,frontend,backend,execute,memory,privileged,observe}`。新增文件必须放入职责对应的 package，不要重新创建 flat `openla500.ooo` 或 `openla500.pipeline`。

## 固定配置

配置入口是 `openla500.core.OooCoreConfig.FourIssueThreeCommit`。当前实现有意固定为 4 发射、5 回写、3 提交，不保留另一套可变宽逻辑。

| 结构 | 配置 |
| --- | --- |
| Fetch / decode / rename / dispatch | 4 / 3 / 3 / 3 |
| Execution issue / writeback / commit | 4 / 5 / 3 |
| Physical registers / ROB | 64 / 32 |
| Instruction buffer / dispatch queue | 8 / 8 |
| Per-port IQ / LDQ / STQ / store-data queue | 8 / 8 / 8 / 8 |
| MSHR | 4 |
| L1I / L1D | 2-way，64 sets，64B line，8 KiB each |
| Shared L2 | 2-way，512 sets，64B line，64 KiB |
| Reset vector | `0x1c000000` |
| TLB | 32 entries，官方 `TLBNUM=32` |

四个发射端口分别是 `alu-csr`、`alu-div`、`alu-branch-mul` 和唯一的 `load-store`。第五条写回通道容纳流水化乘法等 completion；ROB 始终按程序顺序最多提交三条。

## 数据流与精确性

~~~text
translation/L1I -> frontend(fetch4) -> decode/rename3 -> dispatch
                                                     -> 4 x IQ
                                                     -> 4 x issue / 5 x writeback
                                                     -> ROB ordered commit3
                                                        |-> GPR/CSR/TLB state
                                                        |-> cache/AXI side effects
                                                        +-> Chiplab/DPI observation
~~~

- 前端每次提供四条 32-bit 指令，解码、重命名和 dispatch 每拍最多三条。L1I 对各 way 并行预解码，再由 tag 命中选择结果，避免把 BRAM way mux 串在分支译码路径上。预测器为四银行同步 BTB/PHT，并维护 GHR 和 speculative/architectural RAS。
- RAT 保存投机映射，FreeList 使用 head/architecturalHead/tail 环形队列。flush 回退投机 head，commit 更新架构映射并释放旧物理寄存器。写 r0 或无 GPR 目的的 uop 固定 `pdst=0`。
- 四个 8-entry IQ 按端口能力保存 uop，并按年龄紧凑排列。单周期 ALU 和固定延迟 MUL 使用窄 tag 提前唤醒；数据只在 PRF operand 边界转发。可变延迟 DIV 经 ROB 寄存写回唤醒。
- Store 地址和数据解耦：地址进入 LSU IQ，数据进入独立 store-data queue，二者按 ROB/STQ identity 在 LSQ 汇合。普通 store 只有地址和数据都就绪后才完成，只有 ordered commit 后才能产生外部写副作用。
- Load 调度在选择边界寄存不可变 payload；同拍 AGU 命中时旁路新地址。已接受的响应用 ROB generation pointer 和 recovery epoch 匹配 LDQ entry，拒绝 flush 后的旧响应误完成复用槽位。
- ROB 接受 completion 后寄存 one-hot 目标及 payload，下一拍同时开放 commit、写 PRF 并唤醒 IQ。三条 commit payload 使用同步 bank 预取；exception、ERTN、CSR、TLB、CACOP、barrier 和 IDLE 只在 ROB head 处理。
- L1D 和共享 L2 各支持 4 个实际 MSHR。L1D 有 8 个 load waiter，可合并同 line 请求，并在目标 beat 到达时提前返回；共享 AXI bridge 允许 cached read ID 4..7 交错返回。
- branch recovery、exception redirect 和 privileged side effect 都经过统一 flush/redirect 边界，保证 younger ROB/IQ/LSQ/frontend 状态一起撤销。Chiplab/DPI 只观察提交，不旁路提交逻辑。

## 内部接口

### OooCore

`openla500.core.OooCore` 是不含 CSR/TLB/AXI 外壳的核心：

| 方向 | 接口 | 语义 |
| --- | --- | --- |
| master/slave Stream | `instructionTranslationRequest/Response` | 取指虚拟地址到物理地址、MAT 和异常 |
| master/slave Stream | `dataTranslationRequest/Response` | LSU 翻译，携带 ROB/pdst 上下文 |
| out/in | `memoryRead*`、`memoryWrite*` | 64B cache line 读写 |
| out/in | `uncachedInstruction*`、`uncachedData*` | 设备或禁 cache 访问 |
| in/out | `systemRead*`、`csrWrite*`、`exception*` | ROB head 系统状态和精确异常 |
| out | `commit[3]`、`commitValid`、`recovery` | 有序提交和恢复 |
| in | `externalRedirect*`、cache invalidate、reservation | ERTN、IDLE、维护和 LL/SC 环境 |

### OooCoreSystem 与官方 top

`OooCoreSystem` 在同一 `aclk` 和同步高有效内部 reset 域内实例化 CSR、32-entry TLB、地址翻译、IDLE 控制器、cache hierarchy 和 `OooAxiLineBridge`。CSR/TLB/cache maintenance/LLSC side effect 只在提交边界应用。

官方 `core_top` 保持 49 个端口：

| 分组 | 端口合同 |
| --- | --- |
| clock/reset/interrupt | input `aclk`、低有效 `aresetn`、`intrpt[7:0]` |
| AXI read address | output `arid[3:0]`、`araddr[31:0]`、`arlen[7:0]`、`arsize[2:0]`、`arburst[1:0]`、`arlock[1:0]`、`arcache[3:0]`、`arprot[2:0]`、`arvalid`；input `arready` |
| AXI read data | input `rid[3:0]`、`rdata[31:0]`、`rresp[1:0]`、`rlast`、`rvalid`；output `rready` |
| AXI write address | output `awid[3:0]`、`awaddr[31:0]`、`awlen[7:0]`、`awsize[2:0]`、`awburst[1:0]`、`awlock[1:0]`、`awcache[3:0]`、`awprot[2:0]`、`awvalid`；input `awready` |
| AXI write data/response | output `wid[3:0]`、`wdata[31:0]`、`wstrb[3:0]`、`wlast`、`wvalid`；input `wready`、`bid[3:0]`、`bresp[1:0]`、`bvalid`；output `bready` |
| debug | input `break_point`、`infor_flag`、`reg_num[4:0]`；output `ws_valid`、`rf_rdata[31:0]`、`debug0_wb_pc[31:0]`、`debug0_wb_rf_wen[3:0]`、`debug0_wb_rf_wnum[4:0]`、`debug0_wb_rf_wdata[31:0]`、`debug0_wb_inst[31:0]` |

compatibility wrapper 上电后保持内部 reset，直到至少采样到一次 `aresetn=0`；之后沿用官方同步复位时序。非法 `TLBNUM` 会保持 reset。`arlen/awlen` 的 8-bit 宽度和未使用的 debug 端口都是官方合同，不能因当前 SoC 未连接而删除。

### Cache/AXI line 边界

`OooCacheContract` 固定 `LineBytes=64`、`BeatBytes=8`，每行 8 个内部 beat。`OooSharedReadMshrRouter` 是 4 个全局 line-read ID 的唯一所有者，记录 I/D owner 和 client local ID。L1I 只有一个 local miss context；L1D 和 L2 可以保持多个不同 set miss，并允许 hit-under-miss。

`OooAxiLineBridge` 将 cached read 映射到 AXI ID 4..7，IDs 2/3 用于 uncached instruction/data read。数据侧 refill 使用从 critical beat 开始的 16 个 32-bit WRAP transfer；line write 和 uncached traffic 保持全局有序。任何 line geometry、ID 或 burst 改动都必须同步更新合同测试。

## 生成与验证

迁移后的主机需要设置以下本地环境变量，它们不属于仓库状态：

- `CHIPLAB_HOME`：官方 Chiplab 验证树；
- `VIVADO_HOME`：Vivado 2023.2 安装根目录；
- `FPGA_CLIENT_HOME`：远程评测客户端；
- `FPGA_WORK_ROOT`、`FPGA_ARTIFACT_ROOT`：可删除的构建和包目录。

从仓库根目录执行本地门禁：

~~~bash
make scala
make test
make python-test
make generate-core
make port-check
make lint
make yosys-check
make publish-check
~~~

生成完成后，`build/core_top/package/rtl/mycpu_top.v`、`rtl/mycpu_top.v` 和 replacement ledger 的 SHA-256 必须一致。不能手工修改生成 Verilog。

官方 Chiplab 仿真需要 Linux 文件系统：

~~~bash
export CHIPLAB_HOME=/path/to/chiplab
cp rtl/mycpu_top.v "$CHIPLAB_HOME/IP/myCPU/mycpu_top.v"
cd "$CHIPLAB_HOME/sims/verilator/run_prog"
./configure.sh --run func/func_lab19 --disable-simu-trace --output-uart-info
rm -rf obj_dir output
make -j8 verilator
make testbench
make soft_compile
make simulation_run_prog TIME_LIMIT=1300000
~~~

`configure.sh`、`make verilator` 和 `make soft_compile` 不能省略，否则可能复用旧配置、旧 `Vsimu_top__ALL.a` 或缺失 `rom.vlog`。最终必须同时检查 DiffTest、syscall 和 end PC。

standalone Vivado 只验证 core_top 自身，不代表完整 SoC 闭合：

~~~powershell
& "$env:VIVADO_HOME\bin\vivado.bat" -mode batch `
  -source tools/ooo_core_top_synth.tcl `
  -tclargs (Resolve-Path 'rtl/mycpu_top.v').Path (Join-Path (Resolve-Path '.').Path 'build/vivado/core_top')
~~~

完整 SoC 构建和板测必须使用已提交的完整 40 位 commit。默认直接跑 `perf20`，只有暴露功能问题时才回到 `func58`；同一候选做三次严格串行真实评测并取最低 `soc_count`。板测 passed、bitstream 成功和时序闭合是三个独立结论，必须分别记录。远程客户端命令模板、版本要求、包哈希和当前 Job ID 均在 status.yml。

## 迁移清单

1. 从远端检出最新 `dev-OoOE`；当前 RTL 基线是 status.yml 的 `baseline.rtl_commit`，其后的纯文档提交不改变 RTL。
2. 设置上述五个环境变量。路径可以位于任意磁盘，不得把本机绝对路径写回仓库。
3. 不迁移 `build/`、Vivado runs、WSL 临时目录、`.fpgajob` 或远端结果缓存；它们都能从提交、包哈希和 Job ID 重建或重新获取。
4. 开始修改前确认 `git status` 干净，并核对 `rtl/mycpu_top.v` SHA-256 与 status.yml 一致。
5. CPU 功能只改 `spinal/src/main/scala`；重新运行 `make generate-core` 发布 Verilog。禁止引入非自动生成的 Verilog。
6. 新候选按“本地门禁、官方仿真、完整 SoC implementation、三次真实 perf20”的顺序验证。任何 RTL 改动都不能继承当前 WNS 或板测 verdict。

## 已知风险与后续入口

- 当前 setup margin 只有 `+0.036678 ns`。最差 CPU 路径是 ROB `stagedPdst` 高扇出到 issue-queue payload clock enable，9.582 ns 数据路径中 8.153 ns 是布线。
- 当前闭合版本比性能参考慢 620,197 cycles（0.84%）。已知可能的周期代价来自注册式 shared-L2 miss request 和 scheduler input window；这是后续分析入口，不是未经验证的修复结论。
- 本次只证明当前 commit/profile 的三次 `perf20` 20/20，不自动扩大为 random DiffTest、Linux 或其他 profile 的完整等价声明。
- 停止状态为：没有活动的综合 run 或板测任务；优化工作已在建立 100 MHz 闭合基线后主动停止。

## 历史证据

当前迭代的完整构建、时序和三次板测证据在 [L1I 并行预解码迭代日志](../logs/refactor/20260728-l1i-parallel-predecode-timing/iteration.md)。更早试验保留在 `logs/refactor/`，只用于追溯，不能用其中的“当前”“待执行”覆盖 status.yml。原始标量性能对照保留在 `baseline.txt`。
