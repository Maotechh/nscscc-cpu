# Draft PR：建立 openLA500 mul golden harness

状态：`awaiting_implementation`。本 prerequisite 只扩展可执行验证入口，不替换 `rtl/mul.v`，不自动创建 PR 或合并。

## 目标

为锁定 `a158aa8:rtl/mul.v` 建立 cycle-accurate directed/random oracle，明确 reset hold、首拍采样、signed/unsigned 和 64-bit 结果合同，并保持现有 ALU gate 兼容。

## 非目标

不修改 CPU RTL、Spinal mul 实现、流水/缓存/性能，不声明功能、Linux、FPGA 或完整重构通过。

## 回退

revert 本 prerequisite 提交即可恢复当前验证入口。
