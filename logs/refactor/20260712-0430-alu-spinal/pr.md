# Draft PR：以 SpinalHDL 等价替换活动 ALU

## 状态

`awaiting_implementation`。这是基于 `refactor/20260711-1533-component-overlay` 的 stacked Draft；按用户要求不自动创建 PR，不自动 ready 或 merge。

## 目标

用 Scala 手写真源生成精确兼容 `a158aa8:rtl/alu.v` 的组合 `alu`，并以端口检查、directed/random 差分、Yosys 全输入形式等价、static gate 和 chiplab diagnostic 证明边界行为。

## 非目标

- 不改 decode/pipeline/cache/CSR/mul/div。
- 不做性能优化或 FPGA job。
- 不把 locked whole-CPU 的既有失败称为候选 PASS。

## 回退

revert 本 Draft PR；历史 ALU 继续保留为 oracle 与稳定实现。
