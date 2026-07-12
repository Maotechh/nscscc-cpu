# Draft PR：以 SpinalHDL 重构 openLA500 mul 叶子

状态：`awaiting_pr / draft only`。分支
`refactor/20260712-1651-mul-spinal` 已推送；本草稿不自动创建 PR、标记 ready 或合并。
实现与 review target 为 `f6c55e6dcb42761c283febf99460214452628fd0`，base 为
`a17b30165a70f2eae37a6f7074f5fbf7a25ee688`。

## 目标与合同

只迁移活动 `a158aa8:rtl/mul.v`：精确六端口、显式 `mul_clk` ClockDomain、同步
reset-hold，以及每个 active 上升沿捕获 signed/unsigned 32x32 的完整 64-bit product。
不修改 decode、pipeline、cache、CSR、AXI 或性能策略。

生成 RTL 为 1260 bytes，SHA256
`5ff75243dd504bf74c01645862364cd416dffc554d64c82dea6be8f7181660d6`；
replacement 只覆盖 `rtl/mul.v`。

## 验证

- clean LF clone 自动化 193/193，Scala 4/4，全部 0 skip；
- 双生成字节一致，426 个锁定 dependency artifact 前后稳定；
- exact port、Verilator 5.020 `-Wall` 0 warning、Yosys 0.33 PASS；
- 32 directed + 4096 random，共 4128/4128 cycle differential，0 skip；
- candidate 2-state 时序合同证明与两项负控 3/3；
- Windows/chiplab doctor PASS；
- committed mixed overlay provenance/integrity PASS。

官方 `func_lab19` 的 candidate 和 mixed 均 FAIL：同一 `0x1c07c79c` 首错、
172552 instructions、602903 cycles、相同 trace；mixed 仍有 640 条未批准 warning。
因此不得声明 func 或 integrated PASS。

Vivado 2023.2 只完成叶子 `synth_design`。candidate 为 50 LUT / 34 FF / 4 DSP，
但有 63 条未批准 warning；未运行 implementation/bitstream，且无有效 Fmax。

## 评审、风险与回退

两次 Claude bridge job 均在模型启动前失败，`claim_review=unavailable`；独立 Codex
审查不能替代 Claude。golden Booth/Wallace 完整 formal 等价也因 solver timeout 保持未证明。

状态保持 `implementation_in_review`。回退方式为 revert 本迭代提交，并继续使用
`a158aa8:rtl/mul.v`。不得自动合并。
