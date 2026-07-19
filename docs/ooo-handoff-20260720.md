# 4 发射 / 3 提交 OoO 重构交接

更新时间：2026-07-20  
工作分支：`dev-OoOE`  
分支起点：`ad6551afe009652b5562f200bd0d76f641d56a76`  
状态：按用户要求暂停，未提交，官方 CPU top 尚未切换到 OoO 后端。

## 1. 目标与固定配置

当前目标已经从“可配置扩到 4 提交”收敛为唯一实现：

| 项目 | 固定值 |
| --- | ---: |
| Fetch slots | 4 |
| Decode / Rename / Dispatch | 3 / 3 / 3 |
| Execution issue ports | 4 |
| Writeback lanes | 5 |
| Ordered commit | 3 |
| PRF | 64 x 32-bit |
| ROB | 32 entries |
| IQ | 4 x 8 entries |
| LDQ / STQ | 8 / 8 entries |
| MSHR | 4 entries |
| L1I / L1D | 各 2-way x 64 sets x 64B = 8 KiB |
| L2 | 2-way x 512 sets x 64B = 64 KiB |

`OooCoreConfig` 现在会拒绝其他流水宽度。保留的 cache/queue 几何参数用于复用组件，不会
生成第二套后端数据通路。

参考实现为上一级 `ysyx-workbench` 的 `la32r-linux` 分支。其关键参数是 fetch4、ISSUE3、
MACHINE4、WB5、COMMIT3、PRF64、ROB32、IQ8、LDQ/STQ8、MSHR4 和 64B cache line。详细对比
及迁移顺序见 `docs/ooo-refactor-plan.md`。

## 2. 已实现内容

新代码位于 `spinal/src/main/scala/openla500/ooo/`：

* `OooCoreConfig.scala`：固定 4 execution issue / 3 commit 的硬件契约和 cache 几何。
* `OooUops.scala`：decode、rename、completion、commit、recovery、LSQ allocation bundle。
* `OooLa32rDecoder.scala`、`OooWideDecode.scala`：无旧标量流水状态的纯 LA32R 解码和
  fetch4 -> decode3 边界。
* `OooRegisterStructures.scala`：spec/architectural RAT、64 项 ready scoreboard、PRF 和
  三路 FreeList。FreeList 使用 one-hot 首位提取，不再生成 64 项串行优先链。
* `OooRob.scala`：三路分配、五路 completion、三路顺序提交、完整 ROB pointer stale
  response 拒绝、精确 exception/branch recovery。
* `OooIssueQueue.scala`：每执行端口 8 项 IQ；完整 Uop 保存在固定 payload slot，只压紧
  3-bit 槽位顺序，避免全宽 Uop 搬移。IQ 满时不做同周期出队/入队旁路，以切断调度到
  rename/FreeList 的长组合路径。
* `OooBackend.scala`：rename、ROB、IQ、PRF、completion 串接；IQ/PRF 与执行之间已有每端口
  一项弹性 issue-read 流水级，稳态仍可四端口同时发射。
* `OooExecutionCluster.scala`：四个执行端口、旧核已验证 ALU、1-cycle multiply、32-cycle
  divide、branch resolve、CSR read、AGU；multiply 使用第五 completion lane。
* `OooLsqAllocator.scala`、`OooLoadStoreQueue.scala`：rename 预占 LDQ/STQ；store 只在 ROB
  commit 后发往 cache；load 对未知老 store 保守等待；单个完整覆盖 store 可转发；完整
  ROB pointer 拒绝 stale AGU/response；对齐错误生成精确异常。
* `OooCommitAdapter.scala`：三路 ordered commit 收敛为标量 CSR/TLB/exception/debug side
  effect 接口。
* `OooCacheContracts.scala`、`OooCacheArray.scala`：64B/512-bit line contract、4-entry MSHR
  原型，以及可推断 BRAM 的 L1/L2 tag/data array。
* `OooBackendWithExecution.scala`：集成 backend、execution、LSQ、commit adapter，对外暴露
  ordered D-cache request/response。
* `GenerateOooBackend.scala`：独立生成 OoO 后端 RTL。

测试入口为 `spinal/src/test/scala/openla500/ooo/OooCoreSpec.scala`，独立综合脚本为
`tools/ooo_backend_synth.tcl`。

## 3. 已验证结果

最后一次定向命令：

```powershell
$env:SBT_OPTS='-Xms512M -Xmx3G -Dsbt.supershell=false'
& "$HOME\.codex\tools\sbt-1.10.11\sbt\bin\sbt.bat" -batch `
  "testOnly openla500.ooo.OooCoreSpec"
```

结果：10 tests passed，0 failed。覆盖配置约束、backend、decoder、wide decode、execution、
集成 LSQ 后端、commit adapter、MSHR 和 L2 array 的 Spinal elaboration/Verilog generation。

此前运行全仓 `sbt test` 得到 40 tests：28 passed，12 failed。12 个失败全部是 Windows 找不到
`verilator_bin.exe` 的进程启动错误，不是断言失败；新 LSQ 接入后尚未重跑全仓仿真。

Vivado 2023.2，器件 `xc7a200tfbg676-2`，仅对独立后端施加 10 ns clock：

| 版本 | LUT | FF | WNS @ 10 ns | 结论 |
| --- | ---: | ---: | ---: | --- |
| 初始 integrated backend | 57,827 | 19,473 | -8.506 ns | 调度/PRF/乘法同拍，过长 |
| static scoreboard | 57,894 | 19,472 | -9.782 ns | 无收益 |
| stationary IQ + ROB age compare | 51,074 | 19,472 | -21.678 ns | 已放弃 |
| payload slot + order tag | 52,674 | 19,567 | -11.933 ns | 面积下降，时序仍差 |
| 去除 IQ full bypass | 52,749 | 19,568 | -9.613 ns | 切断 dispatch 回路 |
| issue-read elastic pipe | 52,777 | 20,777 | -4.583 ns | 关键流水分级有效 |
| one-hot FreeList | 52,821 | 20,777 | -2.322 ns | 最佳无 LSQ 后端结果 |
| integrated LSQ | 56,785 | 19,976 | -2.301 ns | 当前完整独立后端结果 |

最后一次 integrated LSQ 综合有 0 error、0 critical warning、3999 warnings，并完整生成：

* `spinal/target/ooo-vivado/synth-integrated-lsq/utilization.rpt`
* `spinal/target/ooo-vivado/synth-integrated-lsq/timing.rpt`
* `spinal/target/ooo-vivado/synth-integrated-lsq/ooo_backend_synth.dcp`

当前最差路径约 12.15 ns，从 IQ count/ready 逻辑到另一个 IQ 的 source-ready 状态。层级交叉主要
来自综合器合并 completion/wakeup 逻辑。该结果只是 standalone backend，没有 cache、MMU、
frontend 和 SoC IO placement，不能当作最终频率或性能结论。

## 4. 已确认的不变量

* `p0` 始终 ready 且数据为 0。
* 同一 rename group 内 RAW/WAW 按 lane 顺序处理。
* 旧物理寄存器只在 ordered commit 后释放。
* ROB completion 必须同时匹配 entry valid 和完整 wrap pointer；stale completion 不得写 PRF
  或唤醒 IQ。
* dispatch 必须保持 prefix：老 lane 无法路由时，年轻 lane 不得越过接受。
* serial/CSR 仅在完整 ROB pointer 等于 ROB head 时发射。
* exception 或 branch-mispredict lane 之后，同拍不提交更年轻指令。
* speculative store 不直接修改 cache；只有 committed store head 才能发出 D-cache write。

这些目前主要由结构检查和代码审计确认，仍需 Verilator 逐周期测试。

## 5. 当前明确缺口

以下内容未完成，因此当前实现不能替换比赛 CPU：

1. 官方 `CoreTopCompat` 仍实例化标量流水；没有 generator-time backend switch。
2. 没有 fetch4 instruction buffer、跨 64B line 取指、分支 predictor recovery 串接。
3. LSQ 尚未接 MMU/TLB：`physicalAddress` 暂时等于 `virtualAddress`，`uncached=false`。
4. LL/SC 尚不完整：SC 当前按成功返回 1，没有真实 LLbit、地址匹配和失败路径。
5. LSQ 为保守单 load-head cache request；不支持多个并行 load miss、partial store merge 或
   多 MSHR requester metadata。
6. `OooCacheArray` 和 `OooMshrTable` 只是数组/分配原型；缺 L1 controller、refill、dirty
   writeback、L2 arbitration、AXI 8 x 64-bit burst、uncached/CACOP controller。
7. CSR/TLB/cache-control adapter 尚未接入真实 `OpenLa500Csr`/地址转换/TLB top。
8. recovery 产生了精确信息，但顶层尚未把 recovery 转为 frontend redirect 和全局 flush。
9. 没有 NEMU/DiffTest、func58/81、perf20、Vivado 全 SoC implementation 或 FPGA 实测。
10. 新源文件全部仍是 untracked；没有 commit，也没有改写正式 `rtl/mycpu_top.v`。

## 6. LSQ 恢复后优先审计

`OooLoadStoreQueue.scala` 是暂停前最后加入的高风险模块。恢复后先写仿真，不要继续堆 cache：

1. rename 预占后 AGU 乱序到达，检查 load/store index 和完整 ROB pointer。
2. 未知老 store 阻塞 load；无重叠老 store 不阻塞。
3. 单个 byte/half/word store 完整覆盖时转发并正确 sign/zero extend。
4. partial overlap 和多个覆盖 store 必须等待，不能错误选择旧值。
5. store 在 commit 前绝不产生 `dataRequestValid`；cache backpressure 时保持请求稳定。
6. load response、forward、store AGU completion 冲突时每拍最多一个 LSU completion。
7. byte/half/word misalignment 的 ecode、badVAddr 和精确 flush。
8. flush 后 stale AGU/cache response 不得 completion，不得释放新一代 queue slot。
9. load 在完成后到 commit 前保留 LDQ slot；三路同拍 load commit 正确释放 0..3 项。
10. ROB wrap、LDQ/STQ wrap、队列满/空、同拍 commit/drain/allocation。

特别检查 `OooCacheResponse.data` 的定义。当前 LSQ 假设它是包含目标地址的 32-bit aligned word，
由 LSQ 根据地址低两位做 byte/half 提取；未来 cache controller 必须与此保持一致或修改 contract。

## 7. WSL 环境建议

建议 WSL2 Ubuntu 22.04 或 24.04：

```bash
sudo apt update
sudo apt install -y build-essential git curl make verilator openjdk-17-jdk
verilator --version
java -version
g++ --version
```

继续前请记录上述版本。Scala 工程锁定 sbt 1.10.11；Windows 已安装在
`C:\Users\wxwoo\.codex\tools\sbt-1.10.11`。WSL 可单独下载同版本，或用仓库的 sbt launcher。
为减少 `/mnt/c` 文件系统开销，仿真可在 WSL 的 ext4 工作副本运行，但回写前必须确认没有覆盖
Windows 工作树里这些未提交文件。

优先恢复命令：

```bash
cd /mnt/c/Users/wxwoo/Desktop/NSCSCC/nscscc-cpu/spinal
sbt -batch "testOnly openla500.ooo.OooCoreSpec"
sbt -batch test
```

Vivado 继续在 Windows 执行。独立后端生成与综合命令见 `GenerateOooBackend.scala` 和
`tools/ooo_backend_synth.tcl`。

## 8. Git 与暂停状态

暂停时 `git status --short`：

```text
?? docs/ooo-refactor-plan.md
?? spinal/src/main/scala/openla500/ooo/
?? spinal/src/test/scala/openla500/ooo/
?? tools/ooo_backend_synth.tcl
```

本轮没有 commit。原因是尚未通过完整功能测试和真实性能评估，不满足仓库 AGENTS 流程中的
采纳/提交条件。恢复工作时不要先 commit，也不要把 `spinal/target/ooo-vivado/` 生成物加入版本库。

恢复后的正确顺序是：WSL Verilator 行为测试 -> 修复 LSQ/ROB/IQ -> cache controller/L2/AXI ->
frontend/CSR/TLB/top integration -> 全 SoC Vivado -> func/perf -> 三次 FPGA 实测 -> 决定采纳或回退。
