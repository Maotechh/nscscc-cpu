# Draft PR：增加 pure-Spinal chiplab diagnostic overlay profile

实现一个明确的 diagnostic profile，验证自包含 Spinal `mycpu_top.v` 是否能脱离旧 CPU Verilog 输入运行。默认 locked/mixed overlay 不变；PR 在官方证据完成前保持 draft，不自动合并。

## 结果

- chiplab-doctor、pure overlay、candidate-closure：PASS。
- 官方 configure/build/simulation：exit 0；func_lab19 功能 parser PASS，无 mismatch。
- 严格 smoke gate：FAIL，原因是 40 条 DUT warning 和 365 条官方环境 warning；profile 仍为 diagnostic/non-gate-eligible。
- 未运行：58/81、random、perf20、U-Boot/Linux、Vivado/FPGA。
