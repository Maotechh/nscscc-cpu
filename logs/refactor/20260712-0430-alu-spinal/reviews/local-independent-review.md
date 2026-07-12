# 本地独立只读复审

- 复审对象：最终 publication `d0cd4b33da9a984f66d803943e3e97621124d1ec`
- ALU 实现/tested：`4743235630f69dc96a77ff995ad00a9412d422c7`
- 合同澄清：`ecdc699e10a20c4071f80de55e39f8a4255aa985`（仅文档）
- 身份：独立 Codex 子代理降级复审，不是 Claude 审核。

## C1：模块级 Spinal ALU

结论：`supported_with_narrow_scope`。

Scala 4/4、两次独立 generation、四端口 manifest、模块 Verilator 0 warning、Yosys static、3 个 Scala 测试和 Yosys `equiv_status -assert` 均有结构化结果。形式结果证明的是锁定 Yosys 语义下的 2-state 组合关系，覆盖 78 个 symbolic input bits；不能扩展为 4-state X/Z、时序、综合后资源或整机等价。

## C2：whole-CPU 单例诊断

结论：`supported_with_narrow_scope`。

candidate 与 mixed 都实际执行官方 `func/func_lab19`，均在 172552 instructions、602903 cycles 和 PC `0x1c07c79c` 首错处失败；trace SHA 相同。mixed warning 从 644 降至 642，且没有新增 TIMESCALEMOD，但 mixed `gate_eligible=false`、warning policy 仍 FAIL。

允许的表述是“该单一失败用例未观察到更早可见差异”；禁止写成 CPU 正确、功能 PASS 或集成通过。

## C3：完整重构

结论：`unsupported`。58/81 功能集、random DiffTest、perf20、U-Boot、Linux、Vivado synth/implementation/bitstream 均未执行，且两侧 smoke 都失败。

## 状态建议

模块证据已达到技术上的 leaf differential 门槛；但 Claude required review unavailable 且 `allow_status_promotion=false`，按 AGENTS.md 保持 `implementation_in_review` 和 Draft。不得提升 `differential_pass`、`integrated_pass` 或 `ready`。

## 残余问题

- whole-CPU 仍有 642 条未批准 warning。
- baseline 已知 mismatch 尚未定位，不能归因于 ALU。
- 自动化输出是开发证据，未替代完整 58/81 gate。
- Claude bridge 凭据不可用；需要外部环境修复后重新审核最终 HEAD。
