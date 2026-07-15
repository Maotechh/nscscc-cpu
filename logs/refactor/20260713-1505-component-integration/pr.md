# Draft PR: integrate audited SpinalHDL component replacements

## Scope

在一个分支中组合 AXI bridge、CSR、RegFile、EXE stage、I-cache、TLB/AddrTrans 的既有审计实现，并统一 Makefile、状态源和 lint waiver。未切换活动 `core_top`。

## Evidence

- 日志：`logs/refactor/20260713-1505-component-integration/iteration.md`
- 本地组件 gate：9 个 gate group 执行，9 个通过，0 个 skip。
- 未执行：官方 integration-head func smoke、58/81、random DiffTest、perf20、U-Boot/Linux、Vivado。

## Risk and rollback

该分支只是组件集成底座，不是参赛切换版本。若发现 contract 交叉污染，revert 本 PR；各独立组件分支保留。

## State

Draft only；等待 push 和外部评审，不自动创建或合并 PR。
