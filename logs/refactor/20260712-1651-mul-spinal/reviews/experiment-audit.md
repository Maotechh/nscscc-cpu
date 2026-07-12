# 实验完整性审计

- Auditor：`/root/mul_experiment_audit`
- Review target：`f6c55e6dcb42761c283febf99460214452628fd0`
- Overall：`WARN / pending external recheck`

审计代理核对了最终原始证据，确认以下数字真实存在：automation 193/193、Scala 4/4、
unit 4128/4128、formal 3/3；两份 chiplab 报告均失败，且首错、计数和 trace 相同。
它没有发现用 candidate 输出伪造 golden 或自归一化分数。

审计同时发现当时仓库内 `summary.json`、`iteration.md`、`artifacts.json` 和
`pr.md` 仍索引 pre-commit `a17b301` 证据。这是结果发布一致性 FAIL，不是原始测试数字
伪造。执行代理随后把所有表项改为 `f6c55e6`，增加 tracked evidence/hash，并保持
`func_smoke`、Vivado warning 和 Claude review 为失败/不可用。

审计代理准备复核修正后文件时触发平台用量上限，未产出 fresh final verdict。因此本报告
只能标为 WARN、`pending external recheck`，不能解除 ready/status promotion 阻塞。

## A-F

- A Ground truth：PASS。golden 来自锁定 Git blob；数学 oracle 独立于 candidate。
- B Normalization：PASS。没有归一化得分；只报告原始计数、哈希和首错。
- C Result existence：WARN。原始文件和数字已核实；发布索引已修复但未获独立最终复核。
- D Dead code：PASS。driver、负控和官方 wrapper 都产生被引用的结果。
- E Scope：WARN。叶子证据充分，但官方范围只有一个失败 case。
- F 类型：locked Git golden、独立数学模型、2-state formal、官方 simulation-only、
  Vivado leaf synthesis diagnostic。

C1/C2 只能使用严格限定措辞；C3 不支持。
