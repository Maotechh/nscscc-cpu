# 本地只读审计

- 逐项确认 `reference/component-contracts/icache.json` 与 golden header 为 34 个端口；候选生成文件单模块且 SHA 与 replacement spec 一致。
- `tools/icache_gate.py` 的 golden/candidate 共同驱动包含随机请求、AR backpressure、refill beat 间隙、uncache、CACOP、TLB cancel 和同步 reset；事务级负控在 cycle 7 检出 `rd_req` 禁用。
- chiplab diagnostic overlay 使用 committed source head `528b79ca...` 和 committed replacement blob；官方 `func_lab19` 构建/执行命令返回 0，但 wrapper 状态为 diagnostic、`gate_eligible=false`、`candidate_locked=false`、`baseline_exact=false`，不能称为功能通过。
- 未覆盖项：四态 X 传播、FPGA 资源/时序、完整 58/81、random DiffTest、Linux；这些保持 open/blocking。
