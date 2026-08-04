# 当前 CPU 对非浮点 Linux/完整系统要求的差距判断

> 本文同步自 NSCSCC2026 根工作区 `Info/CurrentDesign/linux-system-gap-audit.md`；
> 功能验收合同位于根工作区 `docs/linux-system-requirements.md`。

## 1. 审计口径

本判断对照根工作区 `docs/linux-system-requirements.md` 中的非浮点 LA32R Linux/完整系统实现要求，审阅当前活动 OoO CPU 的 Scala/SpinalHDL 源码和可复现验证记录。当前候选源自 `dev/ECHO` 的 `60fba481888a8f7e5a2f0ba0b76c91422a117309`，功能实现提交为 `6bbca9b`，生成 RTL SHA-256 为 `137657aa0c594334568cc386571d13aa9cdc828c8fc45c56ed421be15912c209`。固定集成平台为 Chiplab `c398d274812f164d387146fa7d8f612a4a1296d9`。

- **满足**：当前 RTL 已有对应实现，并通过定向测试、随机仿真和完整 SoC 门禁。
- **部分满足**：主要实现存在，但平台范围或端到端证据仍有限。
- **未满足**：存在明确体系结构缺口，或缺少要求中的真实系统验收。

## 2. 总结论

> 当前 CPU 的已知 Linux 体系结构缺口已在本地 RTL 和软件仿真范围内闭环，但 **尚未满足 Linux 总体验收**。

本轮完成了精确 `CACOP`、配置派生 `CPUCFG`、64 B 粒度 LL/SC，以及 MMIO/AXI 错误与恢复路径；原有 `DBAR/IBAR` 闭环继续成立。锁定门禁、Chiplab 功能测试、perf20、干净 Linux DiffTest、三个随机 AXI seed 的 200 ms Linux DiffTest、Vivado 2023.2 的 perf 100 MHz 与 func 平台默认时钟完整 SoC 实现，以及当前候选真实团队板 `perf20`、`func58` 均通过。

仍缺少当前候选在真实 FPGA 上的 U-Boot/PMON、Linux 内核完整启动、Buildroot shell 和文件/进程/页错误/原子/定时器/I/O 操作证据。因此不能把 early-console 或 perf20 结果升级为“Linux 已满足”。

## 3. 当前能力与证据

| 项目 | 判断 | 当前证据 |
| --- | --- | --- |
| 68 条目标指令与特权框架 | 已有 | Scala 译码、CSR、32 项 TLB、地址翻译、精确提交、`IDLE` |
| `DBAR/IBAR` | 满足 | memory epoch、ROB-head 排空、Cache/AXI 双周期静止、IBAR L1D/L2/L1I 维护和 `PC+4` 重取 |
| `CACOP` | 满足 | L1I/L1D/L2 的 Store Tag、Index、Hit 单行维护；脏行写回、Hit 翻译异常和维护 token 均有定向测试 |
| `CPUCFG` | 满足 | 从 `OooCoreConfig` 派生，默认 `.16/.17/.18/.19` 为 `0x1d/0x06070001/0x06060001/0x06090001` |
| LL/SC | 平台范围内满足 | 64 B line 保留粒度；uncached LL 不建立 reservation，uncached SC 失败且不写；平台限定单核、非一致性 DMA |
| MMIO/AXI | 本地满足 | uncached store 等待 B，非 OKAY 形成 ADEM，检查 response ID；cached writeback B 错误在仿真中断言 |
| Cache/AXI 响应仲裁 | 满足 | cached L1D 与 uncached 响应同拍时以一项 deferred response 保存 cached 响应，随机 AXI Linux 死锁已消除 |
| 本地 RTL 门禁 | 满足 | `make cpu-check`：Scala 161/161、Python 364/364、port/lint/Yosys/publication 全通过 |
| Chiplab 功能 | 满足 | `func_lab19`、`func_advance` 在 seed `1`、`19557`、`5570815` 全通过 |
| perf20 | 满足 | 20/20，总 CPU cycles `83,234,731`；相对即时基线 `83,234,678` 为 `+53`，即 `+0.000064%` |
| 完整 SoC 100 MHz | 满足 | bitstream 成功，DRC 0 Error，WNS/TNS `+0.044/0 ns`，WHS/THS `+0.050/0 ns` |
| 团队板 perf20 | 满足 | Job `20260803-220447-d9b5b478`，20/20；选慢值总 CPU count `79,524,833`，同环境 main 对照仅差 `-599`（`-0.000753%`） |
| 团队板 func58 | 满足 | Job `20260803-223955-1ceb232c`，58/58；实际 `32.726797 MHz`，`F0/FF/A5` 均到达 `0x3A00003A` |
| Linux 端到端 | 未满足 | Verilator 到 early-console；当前候选尚无真实板上 shell |

## 4. 已闭环的体系结构语义

### 4.1 `DBAR/IBAR`

8 位 speculative/committed memory epoch 阻止年轻 cached、uncached/MMIO load 和 store 越过栅障。ROB-head 栅障按 ROB pointer 等待旧 store，并要求 L1D、共享路由、L2 和 AXI bridge 连续两个周期静止。`IBAR` 依次执行 L1D、L2 writeback-invalidate 和 L1I invalidate，最终 AXI 响应结束后才完成，并从 `PC+4` 重取。flush 恢复 speculative epoch，迟到维护响应不能写回已回收 ROB。

**状态：满足。**

### 4.2 精确 `CACOP`

`CACOP` 已纳入 memory epoch，并以完整 code、VA/PA、ROB pointer 和 recovery epoch 在 ROB head 串行执行。Hit 类走普通 load 翻译并形成精确 TLB 异常但不检查对齐；Index/Store Tag 直接使用 VA 选择 way/index。L1I、L1D、L2 分别实现 Store Tag、Index、Hit；数据 Cache 脏行先写回再失效，Hit miss 无副作用完成。L1I 操作不再扩散为 L2 全局失效，commit adapter 也不再重复发全局维护脉冲。

定向测试覆盖 3 个 Cache、3 类操作、clean/dirty、hit/miss、错误 way、无关行保持、PLV3/TLB 异常、未对齐地址、背靠背操作、flush 和迟到完成。

**状态：满足。**

### 4.3 配置派生 `CPUCFG`

Cache 几何由 `OooCoreConfig` 单一来源生成，并对 ways、sets、line bytes 的二次幂和字段可编码性做 elaboration 断言。默认值正确报告 8 KiB 2-way L1I/L1D 和 64 KiB 2-way L2；未实现的 FPU、向量和未知索引返回零。默认及两组自定义 geometry 已通过测试。

**状态：满足。**

### 4.4 LL/SC 平台语义

reservation 地址宽度由 `xlen - dataCache.offsetWidth` 派生，默认比较 PA `[31:6]`。CSR、commit adapter、core、backend 和 LSQ 使用同一宽度。同一 Cache line 内的 store 会使 SC 失败；相邻 line 不会。uncached LL 不建立 reservation，uncached SC 不产生写事务；异常、ERTN/KLO、WCLLB 清除规则保留。

当前平台明确限定为单核、非一致性 DMA。未来加入一致性 master 时，必须增加外部完成 store 的 reservation invalidation 事件；在此之前不声明多核/一致性 I/O 支持。

**状态：在当前平台范围内满足。**

### 4.5 异常、MMIO 和 AXI 恢复

数据读错误归为 `ADE/ADEM`、`EsubCode=1`，取指错误保持 `ADE/ADEF`、`EsubCode=0` 并记录 BADV。uncached/MMIO store 在 AXI B 响应后完成，非 OKAY 响应回传 LSQ 形成精确 ADEM，并检查 AXI response ID。无法归属到已退休 store 的 cached writeback B 错误按平台违约在仿真中断言，而不是伪装成精确异常。

随机 AXI delay 曾暴露 cached L1D 和 uncached 响应同拍时丢失 L1D pulse 的真实死锁。共享层现以一项 deferred response 保存该响应；修复后 seed `1`、`19557`、`5570815` 均跑满 200 ms、约 41.69 M instructions，无 DiffTest 失配。干净 Chiplab harness 的 50 ms 官方等价检查也通过。

**状态：本地 RTL、定向测试和随机 DiffTest 范围内满足。**

## 5. FPGA 实现证据

Vivado 2023.2 在 `xc7a200tfbg676-2` 上完成 `perf 100 MHz` 全量 synthesis、implementation 和 bitstream：

- 实际 CPU/sys/DDR 时钟为 `100/100/200 MHz`；
- setup WNS/TNS 为 `+0.044/0 ns`，hold WHS/THS 为 `+0.050/0 ns`；
- DRC 为 0 Error、27 Warning；route 为 0 failed/unrouted/partial nets；
- Slice LUT `88,967`，Slice Register `53,697`，BRAM tile `65.5`，DSP48 `8`；
- bitstream SHA-256 为 `6302203cd181748ce5a703312843b5ae80c824b8c94c150151eca05a2e191986`；
- 归档位于 `Stable_Backup/cpu_60fba481888a_chiplab_c398d274812f_perf_100mhz_20260804-054923_stable/`。

该结果证明当前候选完整 SoC 100 MHz 性能配置时序闭合。独立 func 配置也完成全量实现与 bitstream：实际 CPU/sys/DDR 时钟为 `32.726797/100/200 MHz`，setup/hold WNS 为 `+0.978/+0.052 ns`，DRC 0 Error，bitstream SHA-256 为 `30c8543f99e69e0d312d630a67ffc589590eb82197821d82bcd96b6a1a5b3289`。func 归档位于 `Stable_Backup/cpu_e26ccfa823e8_chiplab_c398d274812f_func_20260804-061935_stable/`。

## 6. 团队板 perf20 与 main 对照

当前候选使用 package SHA-256 `36c1e997335b9785ace7b78c645a689918b243d1c8f6c8ed9e4cff11b29ead37`，在 Job `20260803-220447-d9b5b478` 以 `c398d274...`、`nscscc-system-reset-v1` 和实际 `100 MHz` 运行，20 项均通过。LabAgent 每项运行两次并保留较慢有效值；选中结果总 `soc_count=79,537,915`、总 `cpu_count=79,524,833`。`perf_vio.csv` SHA-256 为 `9e86d7f50b7ad74466a9846b11e31e29285042411b8b6b31bcf96eab4ed31823`。

同一团队板紧接着运行 GitLab CI main `d9bab16...` 的 100 MHz perf bitstream，Job `20260803-221038-4ad4237a` 也为 20/20。main 总 `soc_count=79,537,886`、总 `cpu_count=79,525,432`。当前候选相对 main 分别为 `+29` soc cycles（`+0.000036%`）和 `-599` CPU cycles（`-0.000753%`）；20 个单项的最大绝对 CPU count 差为 `0.109278%`。该结果只支持“普通性能路径无可测回退”，不能把 599 cycles 的差值解释为优化收益。

板测证据分别保存在当前 perf 归档和 `Stable_Backup/cpu_d9bab16_chiplab_c398d27_perf/` 的 `board_jobs/<job-id>/` 下，取回文件 SHA-256 与 LabAgent 结果清单全部匹配。

## 7. 团队板 func58

独立 func bitstream 使用未经改写的官方 c398 metrics 打包，package SHA-256 为 `4d3ebd3754f165d0af4c2e37e33e54bc67f9f5d7619c8a4467025d549cc30687`。Job `20260803-223955-1ceb232c` 在 `nscscc-system-reset-v1` 下终态 `passed`：`F0`、`FF`、`A5` 三个 seed 均到达 `0x3A00003A`，实际 CPU 时钟为 `32.726797 MHz`。`board-summary.txt`、`func_vio.csv`、`programming-summary.txt` 和 `vivado-metrics.txt` 的取回哈希均与 LabAgent 结果清单一致，证据位于 func 归档的 `board_jobs/20260803-223955-1ceb232c/`。

该结果关闭当前候选的 func58 板测缺口，但不覆盖 100 MHz 性能配置，也不证明启动链或 Linux shell。

## 8. 剩余验收路径

1. 在真实 FPGA 依次记录 PMON/U-Boot、DDR/UART/定时器/中断、TFTP、内核解包与入口、MMU/用户态、Buildroot shell。
2. 在 shell 中完成文件、fork/exec、页错误、原子、定时器、串口及网络/存储操作，并保存 UART、Job ID 和全部输入哈希。
3. 只有真实 shell 和系统操作通过后，才能把 Linux 总体状态改为“满足”。
