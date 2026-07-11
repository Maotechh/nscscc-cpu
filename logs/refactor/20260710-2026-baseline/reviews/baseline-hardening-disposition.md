# Baseline hardening finding 处置

- 日期：2026-07-11
- 执行者：主执行代理 Codex
- 性质：对独立只读复审 finding 的中文处置记录；**不是新的独立复审，也不是 Claude 审核**
- Review / Source HEAD：`45043bd8a89b0e4dea3911ed609d128252f0319f`
- Final evidence root：`/tmp/nscscc-baseline-final-45043bd`

`baseline-hardening-rereview.md` 在 final 账本重写前完成，保留其当时发现。随后执行代理没有改写原始 finding，而是完成下列处置；当前报告与 raw artifact 的独立复核以 `experiment-audit.md` 为准。

| Finding | 状态 | 处置与证据 |
|---|---|---|
| candidate 在 `func_lab19` 失败 | `open / blocking` | final run 再次复现 `172552` instructions、`602903` cycles、PC `0x1c07c79c` 的同一 mismatch；见 `evidence/rtl-smoke-summary.json` |
| 644 条未批准 warning | `open / blocking` | DUT 280、官方环境 364；warning policy 保持 FAIL，没有新增全局 suppression |
| Claude bridge 不可用 | `open / blocking` | 两个 job 均在模型启动前失败；见 `claude-raw.md` 与 `claude-summary.json` |
| summary/head/claims 过期 | `fixed` | `summary.json` 绑定 source/review HEAD `45043bd`，每个 gate 含 planned/executed/passed/failed/skipped；状态仍为 blocked |
| commands 使用旧 schema/路径 | `fixed` | `commands.jsonl` 使用 argv/cwd/exit/elapsed/evidence，记录 final doctor/overlay/smoke/Scala 与两次 Claude 失败 |
| artifacts 指向旧 `/tmp` | `fixed` | `artifacts.json` 只索引仓库内 14 个证据文件；大 artifact locator/hash 保存在结构化报告。独立审计复算 14/14 匹配 |
| git-state、失败摘录、iteration、PR、status 过期 | `fixed` | 已全部重写为中文并绑定 final evidence；`validate-iteration` 实跑通过 |
| 无法解析宏 include 可绕过 Scala policy | `fixed at 45043bd` | evaluator 现在拒绝 `unresolved_include_directives`；对应自动化回归包含在 59/59 PASS |
| Scala 测试边界被夸大 | `fixed in claim` | 只声明 12 个 result vector 与 4 个 flag assertion 的 local smoke，不声明 golden differential；见 `scala-format-semantic-review.md` |
| 独立 rtl-static/Yosys 未运行 | `open` | summary 明确记为 planned 2 / executed 0 / skipped 2，不能用于 gate closure |

## 当前允许声明

在锁定 chiplab、工具指纹和 final overlay 下，本轮自动化实际运行并诚实捕获 `a158aa8` 的单一官方 smoke 失败；同一 source HEAD 的 Python automation 59/59、Scala gate 4/4 通过。该证据只支持继续修复 baseline 与自动化。

## 当前禁止声明

不得声明 candidate 是 golden truth、Scala/Verilog 或整核等价、rtl-static/58/81/random/perf/Linux/FPGA flow 通过、完全重构完成、Claude 已审核或 PR 可以 Ready/merge。

结论：处置没有解除主要 blocker。本迭代只能形成 Draft PR；后续在独立 golden-recovery/cacop 分支恢复可执行 baseline，代理不得自动合并。
