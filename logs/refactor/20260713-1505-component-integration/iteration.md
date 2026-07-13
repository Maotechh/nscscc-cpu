# 20260713-1505-component-integration

- Status: local_gates_passed / awaiting_push / awaiting_pr
- Branch / Base SHA / Head SHA: `refactor/20260713-1505-component-integration` / `f621c7a1e056b9f128b86efddbdd2598b3692ecc` / 实现证据头 `2421849dc4f92178b85a594320824b7cfb109351`
- Owner / Agent: integration / Codex
- Selected boundary and selection reason: 把已经分别审计的 AXI bridge、CSR、RegFile、EXE stage、I-cache、TLB/AddrTrans 放进同一分支，先消除组件分支彼此孤立和 Makefile/status/waiver 冲突，再进入整机兼容壳与流水集成。
- Golden reference and locked tool versions: `a158aa8`；Scala 2.13.16、sbt 1.10.11、SpinalHDL 1.14.2、JDK 17.0.19、Verilator 5.020；chiplab `a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`。
- Behavior contract: 本迭代只证明已迁移组件在同一源码树中可编译、可重生成，并继续满足各自锁定叶子合同；不证明它们已由活动 `core_top` 实例化，也不证明整机功能等价。
- Files changed: 汇入六组既有实现/证据提交；合并 `Makefile`、`docs/refactor/status.yml`、`lint-waivers.yml`；新增本迭代日志。
- Functional/performance/resource delta: 未执行整机功能、性能或 Vivado，不能给出整机 delta。
- Rollback: revert 本 integration PR；各独立组件分支不受影响。
- PR URL or awaiting state: `awaiting_push`，未创建 PR，禁止自动合并。

## 合入来源

| 边界 | 原实现提交 | integration 提交 |
|---|---|---|
| AXI bridge | `bb2dbff` | `543bb02` |
| CSR | `9d31913` | `4a874c6` |
| RegFile | `41b93e5` | `6a01570` |
| EXE stage | `4c73068` | `847e536` |
| I-cache | `528b79c` 及后续证据 | `6e37a51..af0cca3` |
| TLB/AddrTrans | `3f10123` 及后续证据 | `5d8ce4b..2421849` |

## Attempts and failures

1. 首次在 WSL 中运行 `scala-check` 和 automation 时，Windows worktree 的 `.git` 指针被解释为工作目录下的错误路径；Scala gate 在 toolchain verification 失败，automation 有 7 个无法读取 golden blob 的 error。
2. 第二次用全局 `GIT_DIR/GIT_WORK_TREE` 修复主仓库解析后，automation 的临时 Git fixture 继承了该环境，4 个隔离测试因此失败。这是执行环境污染，不是 RTL mismatch。
3. 临时把该 worktree 的非跟踪 `.git` 指针切换为 WSL 路径后复跑，automation `316 tests` 全部通过；测试完成后已恢复 Windows 指针。
4. `make generate TARGET=tlb` 初次不存在，按合同返回非零；独立审查后补上 TLB/AddrTrans reproducible generate target 并复跑。初次失败仍保留在日志中。

## Commands and gate results

| Gate | 结果 | 证据摘要 |
|---|---|---|
| scala-check | PASS | format、compile、test compile、test 4/4 PASS |
| automation | PASS | 316/316 tests OK；前两次环境失败已记录 |
| AXI bridge | PASS | 2-run reproducible；port/lint/yosys；8195/8195 cycle checks |
| CSR | PASS | normal/difftest 2-run；port off/on；static；4174 simulated cycles |
| EXE LACC off | PASS | 2-run；port；8192-cycle 2-state lockstep |
| EXE LACC on | PASS | 2-run；port；8192-cycle 2-state lockstep |
| I-cache | PASS | 2-run；34-port；lint/yosys；16096/16096 checks；negative control cycle 7 detected |
| TLB entry | PASS | 8192 random cycles；8258 total cycles；16577 checks；negative control detected |
| TLB/AddrTrans generation | PASS | 两者均 2-run reproducible，产物哈希与 tracked replacement 一致 |
| chiplab doctor | PASS | locked reference、gitlink、tool/file hashes matched |
| official func smoke | NOT EXECUTED | integration head 没有可证明的活动 `core_top` overlay |
| 58/81/random/perf/system/fpga | NOT EXECUTED | 仍被整机活动集成阻塞 |

## Claim boundary

允许声明：上述已审计叶子实现与各自证据可在同一 integration 分支共存，本地重跑的组件 gate 没有发现回归。

禁止声明：活动 CPU 已完全 SpinalHDL 化；`core_top` 接口通过；官方 `func_lab19`、58/81、NEMU random、perf20、U-Boot、Linux 或 Vivado 通过；golden/candidate 整机顺序或形式等价。

已知锁定 `func_lab19` baseline 与此前 mixed candidate 都在 `0x1c07c79c` 首错。本迭代没有重跑该诊断，不能把既有首错扩展为本 head 的测试结果。

## Residual risks

- `core_top`、IF/ID/MEM/WB、D-cache/uncached、BTB、LACC 整机接线、CommitEvent/DiffTest 仍未完成。
- RegFile 在本次 Scala test 中覆盖，但未单独重跑其独立 RTL golden harness。
- EXE lockstep 是固定 seed 的 2-state 证据，不覆盖 X/Z 等价或整机 stall/flush 组合。
- AddrTrans 顶层尚无完整逐拍差分；当前强证据集中在 TLB entry、端口与静态检查。
- Claude 外部审核因缺少 `GEEKPIE_CLAUDE_API_KEY` 不可用；不得表述为 Claude 已通过。
- 独立只读审查发现并修复 TLB/AddrTrans replacement spec 的路径/schema 阻塞；审查原文见 `reviews/local-independent-review.md`。

## Next unblocked candidates

- 先补齐 unified `addr_trans` generate/static target 和活动顶层 overlay manifest。
- 按依赖推进 D-cache/uncached 或 MEM stage；之后才能形成 memory subsystem 集成。
- 建立仅做兼容映射的 `core_top` 壳，并在整机活动逻辑具备后运行官方 smoke。
