# Draft PR：增加 locked golden 的逐组件 diagnostic overlay

## 状态

`awaiting_implementation`。本 PR 只能保持 Draft，不允许代理自动合并。

## Base / 分支 / 日志

- Base：`fec3e1460fb9658329d5221e062c116090ef4d99`
- Branch：`refactor/20260711-1533-component-overlay`
- 日志：`logs/refactor/20260711-1533-component-overlay/`

## 目标

在不复制完整历史 RTL、不修改 locked baseline 默认语义的前提下，为一个已提交 component replacement 建立结构化、fail-closed、可追溯的 chiplab diagnostic overlay。具体 API、测试和结果将在实现后补充。

## 非目标

- 不修复 cacop 或迁移 CPU 模块。
- 不更新 `team_golden_candidate`。
- 不允许 mixed overlay 报告 `candidate_locked=true` 或 `gate_eligible=true`。
- 不声明功能、性能、Linux 或 FPGA gate 通过。

## 回退

revert 本 Draft PR；locked candidate 的原有命令和输出必须保持兼容。
