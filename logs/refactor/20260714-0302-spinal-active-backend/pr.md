# Draft PR: 激活纯 SpinalHDL openLA500 backend

- Iteration: `20260714-0302-spinal-active-backend`
- Base: `78efdf97b6208da3806fcbc02dca69061284d3b7`
- State: `awaiting_next_push` / draft

## 行为合同

- 纯 Spinal `core_top` 保持 49 个官方端口和 `TLBNUM=32`。
- Decode 只接受 EX/MEM 的真实 GPR `writeEnabled` 旁路，不把级占用状态当作 forwarding enable。
- `CommitEvent` 延迟一拍，GPR/CSR 状态实时观察；`DIFFTEST_EN` 下实例化官方七个 DPI 模块。

## 当前验证

- Scala 4/4 PASS，25 tests PASS；新增连续 store forwarding 回归和生成 RTL 接线合同测试。
- Python 自动化 327 PASS、0 FAIL、10 个平台互斥 skip；该项保持 warning。
- 双次生成可复现；package SHA256 `2646383fc6e201c0108c018c780fb4240301beb53e8dfc6eacf00149ab5586cc`。
- 49/49 端口、publish consistency、Yosys hierarchy/check PASS。
- 严格 Verilator lint FAIL，86 条未批准 warning。
- `39501d1` 官方 smoke 已推进 162,373 条真实 DiffTest 提交，首错已定位并完成 unit fix；修复后的官方 smoke 待新提交 overlay 复测。
- func-full、random、perf、Linux、Vivado implementation/bitstream 均未通过，不作完成声明。

## 风险与回退

- 后续整机 mismatch、BTB/RAS、LACC 和 release gates 仍未完成。
- 回退方式：revert 本迭代提交；不得修改或合并 `main`。

日志：`logs/refactor/20260714-0302-spinal-active-backend/`。代理不得自动创建、标记 ready 或合并 PR。
