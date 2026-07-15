# 实验完整性审核

- 状态：`degraded`
- 受测提交：`75523504912c1b390dc1d1e3cddb5c3a0cc43a27`
- 说明：`experiment-audit` 要求的独立 GPT-5.4 Codex MCP 本会话不可调用，因此不能声称完成跨模型 experiment audit。以下仅复用独立只读子代理对结果文件、命令和数字的一致性检查。

## 检查

- 结果文件存在：PASS。最终 Scala、生成、发布、静态和 smoke JSON 已归档。
- 命令实际执行：PASS。smoke 内三个官方命令退出码均为 0，build artifacts 标记 fresh。
- 数字匹配：PASS。功能 parser 为 174034 条指令、610132 拍、零 mismatch；总 gate 为 1/1/0/1/0。
- 作用域：WARN。只有单个 mixed diagnostic case；不得使用“全面”“official PASS”或“完整 BTB”等表述。
- oracle：WARN。使用锁定 NEMU DiffTest parser，但 DUT 是两个 replacement 构成的 mixed overlay，不是 locked candidate。
- warning policy：FAIL。DUT 258、官方环境 364 条 warning 未获批准，standalone strict lint 也失败。

结论：结果文件没有发现 phantom result 或数字错配，但审核为降级模式，claim 只能保持 Draft 且带上述限定。
