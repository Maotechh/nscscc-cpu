# Draft PR: activate the cumulative reachable Spinal replacements

## Scope

在 legacy `core_top` 壳下统一激活 10 个已提交并各自审计过的 Spinal replacement，增加 `lacc_off` 静态可达性检查与负控。本 PR 不迁移新的流水级，不删除 golden Verilog，不改性能策略。

## Evidence

- strict overlay loader 接受 10 个 committed blob，但仅为 diagnostic，`gate_eligible=false`。
- 官方 full hierarchy 原生 build exit 0；严格 warning policy FAIL（DUT 253、官方 373）。
- `func_lab19` 0/1 PASS，在已知 baseline 同点 `0x1c07c79c` mismatch；不得称为功能通过或等价证明。
- 58/81、random、perf20、U-Boot、Linux、Vivado 均未执行。
- Claude bridge 因缺少 `GEEKPIE_CLAUDE_API_KEY` 不可用。

## Risk and rollback

同点首错不证明此前完整 trace 等价；legacy IF/ID/MEM/WB、BTB、perf 等仍为 Verilog。Revert 本迭代提交即可恢复单项 replacement spec。

## State

远端分支已推送，保持 draft/awaiting PR；代理不创建、不合并 PR。
