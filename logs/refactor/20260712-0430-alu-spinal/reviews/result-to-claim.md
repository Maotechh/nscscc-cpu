# Result-to-Claim 结论

- 审核者：独立只读 Codex 子代理；不是 Claude。
- 实现证据目标：`4743235630f69dc96a77ff995ad00a9412d422c7`
- 总结：`partial`（模块 claim 支持，整机 claim 不支持）。

## C1：Spinal ALU 叶子

`supported_with_narrow_scope`。可声明锁定 Yosys 2-state 组合语义下，生成 RTL 端口精确、可复现，并与 `a158aa8:rtl/alu.v` 对 78 个输入变量等价。不能声明 X/Z、时序、综合资源或整机等价。

## C2：官方单例诊断

`supported_with_narrow_scope`。candidate/mixed 的 `func_lab19` 首错、instructions、cycles 和 trace 相同，mixed warning 少两条；两侧仍 FAIL，mixed gate_eligible=false。

## C3：完整 CPU 功能

`no`。当前没有通过的 func gate，也没有 58/81、random、perf、Linux 或 FPGA 结果。

## 下一动作

保持 Draft 和 `implementation_in_review`；先修复 Claude review bridge，再按动态依赖建立 `mul-golden-harness` prerequisite。不要把 ALU leaf 证据写成整机完成。
