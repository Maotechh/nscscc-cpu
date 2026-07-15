# Result-to-Claim 结论

- `claim_supported`: `partial`
- `confidence`: `high`

## 结果实际支持什么

在锁定的单一 `func/func_lab19` 用例中，等字节 `alu.v` replacement 的 mixed overlay 与 locked 侧具有相同的 manifest-bound 输入投影，并产生相同的选定失败观测。identity comparator 自身为 `status=pass`、`gate_eligible=false`。

## 不支持什么

不支持 CPU 功能正确、RTL 形式/时序等价、Spinal ALU 已迁移、完整重构、58/81 func、random、perf、Linux 或 FPGA PASS。两侧真实结果都是 DiffTest FAIL。

## 缺失证据

- 非等字节 Spinal ALU 与 golden ALU 的 directed/random/formal 差分。
- 生成 RTL 的精确端口、无隐式时钟和 source consistency 证据。
- 独立 Verilator lint/Yosys check。
- 能通过的 whole-CPU golden baseline 或更窄的模块级 executable oracle。
- 可用的 Claude claim review。

## 下一步

新开 stacked ALU 迭代，先补齐模块级 golden oracle 和 fail-closed generator，再迁移 14-bit one-hot ALU。whole-CPU smoke 仅作可见回退诊断；本轮不做性能优化。
