# Draft PR：将 Backend AXI 边界收敛为 typed Axi3Compat

## 行为合同

保留官方 `core_top` 的 49 个 raw AXI3/WID/debug pin；仅把 `SpinalCoreBackend` 与兼容壳之间的重复 raw pin 收敛为 typed `Axi3Compat`。不改变 AXI bridge/cache 状态机、payload 位宽、ready/valid 方向或 reset 语义。

## 验证

- Scala gate：4/4 PASS，31 ScalaTest PASS。
- `core_top`：2/2 reproducible；49-port contract、package、publish-check、candidate closure PASS。
- Yosys hierarchy/check：PASS，0 warning。
- Verilator strict lint：FAIL，73 条 `DECLFILENAME/UNUSEDPARAM/UNUSEDSIGNAL`，未 waiver。
- 自动化：381 tests PASS，10 skipped。
- 官方 smoke、58/81、random、perf、Linux、Vivado：尚未完成，PR 必须保持 draft。

## 影响与回退

无已声明性能/资源变化；未运行 Vivado。revert 本迭代提交即可恢复旧 Backend raw pin 接口和旧发布 RTL。不得自动合并到 `main`。
