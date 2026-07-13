# 独立只读审核

## Blocking 及处理

1. 审核时 evidence 尚未提交。处理：最终 evidence commit 必须包含本目录全部 summary、review 和 artifact 索引，推送后核对远端 HEAD。
2. 初始 summary 仍为 pending 且 head 指向 cherry-pick commit。处理：已更新为 clean source commit `f0b5e2410fccba7c69f143dabed3e50da841b5b4`，逐项记录实际 pass/warning/fail。
3. status 的 source_head 初始仍为 base。处理：已改为 clean source commit `f0b5e2410fccba7c69f143dabed3e50da841b5b4`。
4. diagnostic overlay 明确 `gate_eligible=false`，official smoke 明确 FAIL。处理：summary、iteration 和 PR 草稿均保持 `draft`，禁止 integrated/official PASS claim。

## 代码与证据结论

- `active-reachable.json` 和 meta 只新增 `rtl/if_stage.v`；已有 12 个 replacement 未改变。
- locked golden graph 的静态 reachability `selected_count=13`，`if_stage` 可达。
- clean diagnostic overlay manifest 接受 13 个 committed blob，但这只是结构/来源接受，不是 gate pass。
- official `func_lab19` configure/build/simulation 原生命令退出 0，功能判定仍 FAIL；首错 PC `0x1c07c79c`，trace 与 baseline 相同。
- 245 个 DUT warning 和 373 个环境 warning 没有逐条 waiver。
- Claude bridge 因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败，本文件是降级审核，不是 Claude 审核。

## 允许和禁止的 claim

允许：13 项静态可达；13 个 committed blob 被 diagnostic overlay 接受；本次单 trace 未观察到比 baseline 更早的可见分歧。

禁止：active overlay integration PASS、官方功能通过、IF 整机行为等价、58/81/random/perf/Linux/Vivado 通过或完整重构。
