# typed AXI 边界独立只读审查

- 审查者：Codex 子代理 `/root/backend_arch_audit`
- 审查目标：`c81af389d67063d99beb2caf46260df07a0a5a70`
- 基线：`b8962b6c194c11d01747adb2a7269216df01dce3`
- 结论：`accepted_with_open_limits`

## 已接受

- `Axi3Compat` 的 AR/AW/W 为 master，R/B 为 slave；WID、地址、长度、数据和响应宽度与锁定 chiplab 合同一致。
- `CoreTopCompat` 保留 49 个外部端口，25 个 AXI 输出和 11 个 AXI 输入均为逐字段组合映射；本轮没有增加 AXI 状态、握手或 reset 逻辑。
- 修改前后两个已提交 `core_top` RTL 经 Yosys flattened 顺序等价流程证明：18150 个 `$equiv` cell 全部 proven，0 unproven，命令返回 0。
- pure-Spinal diagnostic `func_lab19` 完成 174059 条指令、609660 个周期，以 syscall 结束且未观察到 DiffTest mismatch。

## 已修正

- 所有累计 replacement spec 和 lint waiver 已同步到新 package SHA256 `51e400e3d3c56bed3201c9599224aaaf361c22d8f1dc272054094adc8a9e9ebc`。
- 正式 `scala-check` 已取得 wrapper exit 0；此前外层 timeout 结果不再作为 PASS 依据。
- overlay 清理逻辑现在保留锁定 LICENSE 和 upstream `mycpu.h`，pure profile 不再误删支持文件。

## 未关闭问题

- `typed_axi_boundary_gate.py` 仍是全文正则。mutation 审查证明它会漏检位宽/slice 修改、reset bypass、内部 bridge 接反、反相和注释伪造；该 gate 不能单独证明行为等价。
- isolated strict lint 仍有 73 条未批准 warning；官方 smoke 编译另观察到 DUT 40 条、官方环境 365 条 warning，因此正式 smoke gate 失败。
- pure overlay 是 diagnostic、`gate_eligible=false`；mixed overlay 被遗留 `div.v` 的 Verilator 命名冲突阻断。
- 自动化 381 项中有 10 项 skip，不满足零 skip 合同。
- 58/81、random DiffTest、perf20、U-Boot/Linux 和 Vivado implementation/timing/bitstream 尚无通过证据。
- Claude bridge 缺少 `GEEKPIE_CLAUDE_API_KEY`，远端 GitHub 443 仍未实时确认。

## Claim 判定

- 允许：Backend 与兼容壳之间采用 typed `Axi3Compat`；锁定外部 49-port 合同保持；记录的修改前后生成 RTL 在该 Yosys 流程下顺序等价；本次 diagnostic smoke 功能观察通过。
- 不允许：正式 chiplab smoke PASS、AXI 协议在所有工具语义下完全等价、完整 CPU release ready、58/81/random/perf/Linux/FPGA 已通过。
- PR 必须保持 draft，不能自动合并或提升完成状态。
