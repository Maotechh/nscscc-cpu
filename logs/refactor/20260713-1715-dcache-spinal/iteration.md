# 20260713-1715-dcache-spinal

- Status: draft / awaiting commit、push、PR 和外部审核
- Branch / Base SHA / Head SHA: `refactor/20260713-1715-dcache-spinal` / `a6788aaf36cea5a90512d60194c9e41a5c127860` / 待首次提交后回填
- Owner / Agent: memory / Codex（实现代理：dcache_contract；只读审核：dcache_review）
- Selected boundary and selection reason: D-cache/uncached 是 MEM stage 与已迁移 AXI bridge 之间的主要活动阻塞，锁定 golden 可执行，且不要求同时修改流水或顶层公开合同。
- Golden reference and locked tool versions: `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/dcache.v`，blob `755b5087d0321ab5a41596465c2352dd3ee98a4e`；JDK 17.0.19、Scala 2.13.16、sbt 1.10.11、SpinalHDL 1.14.2、Verilator 5.020、Yosys 0.33。
- Behavior contract: `docs/contracts/dcache.md`；精确保留 35 端口、同步高有效 reset、五态 FSM、单端口同步 SRAM hold、write buffer、dirty eviction、refill、uncached、cancel、PRELD、锁定 golden 的 CACOP 现状和 LFSR。
- Files changed: Scala D-cache 与生成器、可复现 replacement RTL/spec、合同、Makefile gate、Python 差分门禁及自测、status 和本日志。
- Functional/performance/resource delta: 只证明固定 seed 的 12000-cycle 2-state 叶子差分；未执行整机功能、perf、Vivado 资源或 Fmax。
- Rollback: revert 本迭代 PR；活动 `core_top` 尚未引用该 replacement，参赛稳定线不受影响。
- PR URL or awaiting state: awaiting commit/push；不自动创建或合并 PR。
- Next unblocked candidates: MEM stage 与 D-cache/AXI transaction 的活动集成；之后再推进完整 memory subsystem。

## Attempts and failures

1. Windows 直接运行生成器把 POSIX 默认工具根解析成 `D:\opt\...`，因 Scala cache 不存在失败；切换锁定 WSL 工具链。
2. 初版 Scala 有 LFSR 拼写、lookup 优先级、额外 reset、dirty-valid 条件和 SRAM 写拍语义问题；独立审核逐项指出后修复。
3. 初版差分驱动在上升沿后采样 `rd_req`，会漏掉读握手；改为上升沿前采样并比较 pre-edge 输出。
4. 第一版生成 RTL lint 有除 `preld_hint` 外的未使用信号；移除无效状态别名并把 write-buffer offset 收窄为实际使用的 word index。
5. 一次两轮生成期间实现代理仍在更新源码，生成器以 `source_stable=false` 正确失败；源码稳定后重新生成。
6. 早期 1200-cycle raw trace 在 cycle 370 暴露 SRAM 写拍更新读输出；改用 `duringWrite=dontRead`，生成 RTL确认 `if(write) ... else read`。
7. 后续 raw trace 在 `wr_req=0` 的无效 payload 上仍有差异。最终 oracle 按协议在 `data_ok/rd_req/wr_req` 有效时比较 payload，始终比较控制、valid、`dcache_empty` 与 `cache_miss`；没有放宽有效事务。
8. 首次 chiplab doctor 因全局 `GIT_DIR` 污染而把 CPU commit 误认成 chiplab commit；临时修正非跟踪 worktree 指针后复跑通过，并立即恢复 Windows 指针。

## Commands and gate results

| Gate | 结果 | 证据摘要 |
|---|---|---|
| contract | PASS | golden 35/35 ports，blob/SHA256 匹配 |
| scala-check | PASS | format、compile、test compile、Scala tests 4/4 |
| generate | PASS | 2/2，source stable，可复现；RTL SHA256 `35f56d5d...` |
| port/lint/yosys | PASS | 35/35；仅批准 golden 未使用的 `preld_hint`；Yosys check 无告警 |
| cycle diff | PASS | 12000 candidate + 4096 negative，16096/16096，0 mismatch，负控 cycle 8 命中 |
| D-cache gate tests | PASS | 5/5 |
| automation | PASS with known skips | 321 tests OK；311 pass，10 个既有平台/可选工具 skip |
| chiplab doctor | PASS | locked commit/gitlink、symlink、工具版本与哈希匹配 |
| diagnostic overlay | PENDING | 需先提交 replacement 后从完整 commit 加载 |
| official func/perf/Vivado | NOT EXECUTED | 该叶子尚未进入活动 `core_top`，不能形成整机 claim |
| Claude review | PENDING | 提交后提供完整 base/head diff；不可用时按契约记录错误 |

## Claim boundary and residual risks

允许声明：当前 D-cache replacement 在锁定 golden、固定 seed、12000 周期、2-state、有效协议 payload oracle 下没有发现差异，且生成、端口和静态门禁通过。

禁止声明：MEM stage、完整存储系统或活动 `core_top` 已迁移；官方 func 58/81、random DiffTest、perf20、U-Boot/Linux、Vivado 或 FPGA 已通过；完整顺序/形式等价已证明。

剩余风险：

- driver 使用受控小 working set 和固定 seed，不是形式证明或多 seed random；
- invalid channel payload 不参与比较，符合握手协议，但不能用于声明内部节点逐位等价；
- automation 有 10 个既有 skip，未被本迭代消除；
- replacement 尚未从提交后的 strict overlay loader 验证；
- D-cache 仍未被活动 `core_top` 实例化。
