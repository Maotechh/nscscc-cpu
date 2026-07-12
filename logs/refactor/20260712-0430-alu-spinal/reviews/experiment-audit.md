# 实验完整性审计

- 日期：2026-07-12
- 审计对象：实现提交 `4743235630f69dc96a77ff995ad00a9412d422c7`
- 审计者：独立只读 Codex 子代理（不是 Claude/GPT-5.4 专用 MCP）
- 总体结论：`WARN`

## A. Oracle 来源：PASS

模块 formal oracle 直接读取锁定 `a158aa8:rtl/alu.v`；chiplab smoke 直接使用锁定 NEMU、manifest commit 和 committed replacement blob。没有从 DUT 输出生成“正确答案”。

## B. 归一化：PASS

本迭代只报告原始 instructions、cycles、warning 数和 SHA256，没有自归一化分数。

## C. 结果存在性：PASS

local gate summaries、committed RTL、replacement spec、candidate/mixed overlay 和 smoke 报告均有路径、SHA256、大小或 Git blob 绑定；关键 locator 见 `artifacts.json`。

## D. 未执行范围：WARN

func smoke 只有 `func_lab19` 一个 case 且两侧都失败；58/81、random、perf、Linux、FPGA 未执行。自动化 `Ran 137 tests ... OK` 是开发证据，不替代正式功能集。

## E. 结论范围：WARN

证据足以支持 ALU 叶子模块的窄范围形式/端口 claim，不能支持 CPU correctness、集成功能 PASS、完全重构或性能/资源结论。

## F. 评估类型

`simulation_only` 加 `formal_combination`；不是 FPGA 或系统级 release 评估。

## Claim 影响

- C1：supported_with_narrow_scope。
- C2：supported_with_narrow_scope，必须注明单 case、两侧 FAIL 和 mixed gate_eligible=false。
- C3：unsupported。
