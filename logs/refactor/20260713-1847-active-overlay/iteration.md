# 20260713-1847-active-overlay

- Status: `implementation_in_review`，仅累积集成诊断，不是功能 PASS。
- Branch / Base SHA / Overlay source SHA: `refactor/20260713-1847-active-overlay` / `d128e7bb17bd1386e54af0a4b79bc0c768f41ce4` / `1d0cd288419e430042b8a116d6df291fbc0df3ba`
- Owner / Agent: Codex active-overlay iteration
- Selected boundary and selection reason: 激活 legacy `core_top` 壳下已分别完成差分的可达 Spinal replacement，尽早暴露跨模块接口与官方层级编译问题；不迁移新功能，不做性能优化。
- Golden reference and locked tool versions: `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`，chiplab `a2e11b38...`，Verilator 5.020，Vivado 2023.2（本迭代未运行）。

## 行为合同

统一 spec 只激活以下 10 个 target：`mycpu_top`、`mul`、`div`、`exe_stage`（`HAS_LACC` 未定义）、`regfile`、`csr`、`axi_bridge`、`icache`、`dcache`、`addr_trans`。静态检查从锁定 golden 构造 `core_top` 实例闭包，要求每个 target 可达且 spec、metadata 精确一致。

`alu` 与 `tlb_entry` 在 golden 闭包中可达，但分别已内嵌在当前 `exe_stage`/`addr_trans` replacement 的实现边界中，本迭代不重复加入 overlay。此处是“deferred reachable”，不是“Verilog 不可达”。`lacc_core/lacc_demo` 在 `lacc_off` 配置不可达。

## Files changed

- `reference/component-replacements/active-reachable.json`
- `reference/component-replacements/active-reachable.meta.json`
- `tools/replacement_reachability.py`
- `tests/test_replacement_reachability.py`
- `Makefile`
- 本迭代日志、证据与 `docs/refactor/status.yml`

## Attempts and failures

1. 初版静态解析把同一文件的多个 module 共享实例集合，且未处理行内 `` `ifdef HAS_LACC``；只读复核后改为 module block 隔离和宏配置预处理，并增加 `lacc_core` 负控。
2. Claude bridge 已实际启动 job `8052f9033715467b851e52aa67b326d1`，但在模型运行前因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败，不能称为 Claude 审核。
3. 官方完整 hierarchy build 三条原生命令均 exit 0；严格 warning policy 仍失败：DUT 253 条、官方环境 373 条，共 626 条未批准 warning。
4. `func_lab19` 实际执行 172552 条指令，在 `0x1c07c79c` 首次 mismatch：`t0` right `0x000006e2`、wrong `0x00000008`。这与已知 baseline 首错同点，但没有证明此前完整提交序列等价。

## Commands and gate results

| Gate | 结果 | 证据 |
|---|---|---|
| replacement reachability | PASS | 10/10 target 可达；3 个测试含 deferred 与 LACC 负控 |
| Scala format/compile/test | PASS | 4/4，锁定 SBT/Spinal cache |
| automation tests | PASS | 324 tests；314 pass，10 个既有平台/可选工具 skip |
| chiplab doctor | PASS | `evidence/chiplab-doctor.json` |
| strict aggregate overlay | PASS（diagnostic only） | 10 个 committed blob；`gate_eligible=false` |
| official full hierarchy build | 原生命令 exit 0；严格 gate FAIL | fresh build artifact 完整；626 条未批准 warning |
| official `func_lab19` | FAIL | 0/1 PASS，首错 `0x1c07c79c` |
| Claude claim review | unavailable | 缺少 API key，见 `reviews/claude-raw.md` |
| 58/81/random/perf/system/Vivado | NOT EXECUTED | 不得声明通过 |

## Functional/performance/resource delta

仅有单个 `func_lab19` 诊断失败证据。未执行 58/81、随机 DiffTest、20 项性能、U-Boot、Linux、Vivado synth/implementation/timing/bitstream，因此没有功能、性能、Fmax 或资源改善 claim。

## Residual risks

- 同点首错不能排除首错前未被现有 oracle 暴露的微架构/提交差异。
- 253 条 DUT warning 未逐项 waiver，严格 RTL static/full hierarchy gate 未通过。
- legacy IF/ID/MEM/WB、BTB、perf 等仍为 Verilog；Scala 不是活动 CPU 的唯一手写真源。
- aggregate replacement 依赖各叶子先前差分的范围，尚无整机顺序形式等价。

## Rollback

Revert 本迭代提交，恢复逐个 replacement spec；stable/main 分支未修改。不得删除 golden 或改写历史。

## PR / next

- PR: 分支已推送，`awaiting_pr`；不自动创建或合并。
- Next unblocked candidates: 先定位并消除 aggregate overlay 相对 baseline 的 warning/trace 差异证据，再进入尚未迁移的活动流水级；当前不能把同点失败升级为 `integrated_pass`。
