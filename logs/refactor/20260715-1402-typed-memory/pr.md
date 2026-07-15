# Draft PR：将活动 cache/AXI bridge 连接切换为 typed contract

## 行为合同

新增无状态 `OpenLa500TypedAxiBridge`，I/D cache 侧使用 `LineReadWritePort`，AXI 侧使用 `Axi3Compat`；保留 legacy bridge 的全部寄存器、状态机、仲裁和 reset 行为。外部 `core_top` 49-port 不变。

## 验证

- Scala 4/4、31 tests PASS；typed 结构 gate 与 9 项突变负测 PASS。
- fresh generate/package、49-port、Yosys hierarchy/check、candidate closure、publish/reachability PASS。
- old/new `core_top` 在记录的 Yosys structural two-state flow 下 31,106 proven、0 unproven。
- strict lint 因 73 条既有 warning FAIL；automation 有 10 skip，按合同 FAIL。
- committed chiplab smoke 和 claim review 待补，PR 保持 draft。

## 回退与风险

revert 本迭代提交即可恢复 Backend 直接连接 legacy bridge。不得把本轮窄结构/等价证据外推为 58/81、random DiffTest、Linux、性能或 FPGA PASS。不自动合并。
