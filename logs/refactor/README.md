# 重构迭代日志

每次迭代使用独立目录 `YYYYMMDD-HHMM-<scope>/`，日志使用中文。

必须包含：

- `iteration.md`：过程、失败、结论和残余风险。
- `summary.json`：机器可读状态和 gate 计数。
- `commands.jsonl`：实际执行命令、退出码和摘要。
- `artifacts.json`：大文件的哈希和外部位置。
- `pr.md`：PR 草稿。
- `reviews/`：Claude MCP 原始终态、中文处理结论和独立降级复审；bridge 未启动模型时必须明确写 `unavailable`，不得称为 Claude 已审核。

不得只记录成功结果。大波形、Vivado 工程、工具链和完整 simulator log 不提交 Git。
