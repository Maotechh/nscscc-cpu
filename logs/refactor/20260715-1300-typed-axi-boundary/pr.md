# Draft PR：将 Backend AXI 边界收敛为 typed Axi3Compat

## 补充审查结论

- 修改前后 generated `core_top` 的 Yosys 顺序等价证据为 18150 proven、0 unproven；该结论仅覆盖记录的 Yosys flow，不替代 chiplab 功能、随机 DiffTest 或 FPGA gate。
- pure `func_lab19` 仅是 diagnostic 功能观察：174059 条指令、609660 个周期、syscall 结束、无观察到 mismatch；严格 warning policy 失败，因此正式 smoke 仍 FAIL。
- automation wrapper exit 0 但 10 项 skip，按 `AGENTS.md` 总门禁 FAIL。
- 独立审查和 Claude unavailable 记录已归档；PR 保持 draft，不得自动合并。

## 行为合同

保留官方 `core_top` 的 49 个 raw AXI3/WID/debug pin；仅把 `SpinalCoreBackend` 与兼容壳之间的重复 raw pin 收敛为 typed `Axi3Compat`。不改变 AXI bridge/cache 状态机、payload 位宽、ready/valid 方向或 reset 语义。

## 验证

- Scala gate：4/4 PASS，31 ScalaTest PASS。
- `core_top`：2/2 reproducible；49-port contract、package、publish-check、candidate closure PASS。
- Yosys hierarchy/check：PASS，0 warning。
- Verilator strict lint：FAIL，73 条 `DECLFILENAME/UNUSEDPARAM/UNUSEDSIGNAL`，未 waiver。
- 自动化 wrapper exit 0 但 381 项中 10 项 skipped；按零 skip 合同总门禁 FAIL。
- 正式 gate-eligible smoke、58/81、random、perf、Linux、Vivado：尚未完成，PR 必须保持 draft；pure `func_lab19` 只有 diagnostic 观察证据。
- pure `func_lab19` 已有 diagnostic 功能观察通过，但严格 warning policy 失败；mixed profile 仍被旧 `div.v` 阻断，均不构成正式 gate。

## 影响与回退

无已声明性能/资源变化；未运行 Vivado。revert 本迭代提交即可恢复旧 Backend raw pin 接口和旧发布 RTL。不得自动合并到 `main`。

当前 push 状态：`awaiting_push`；GitHub 443 connection reset，cached origin 仍停在 `b8962b6`，`live_remote_unverified`。
