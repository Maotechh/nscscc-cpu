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
- `2e5409a` 官方 smoke 已越过原 `0x1c0752b8`，推进 172,548 条提交后在 baseline 已知的 `0x1c07c79c` 以相同寄存器/PC 状态失败。
- 因此只声明 forwarding 回归已修复；`func_lab19` 仍为 FAIL，不声明整机等价。
- 独立只读审核支持上述窄 claim；Claude bridge 不可用，因此 claim review 为降级 warning，PR 不得标记 ready。
- 降级 experiment audit 核对了结果存在性、数字和范围，结论为 `WARN`；它不是跨模型审核。
- Baseline/candidate 提交计数相差 4，末尾 30 行相同不能解释为完整顺序 trace 等价。
- 仓库 `evidence-check` 因早期 `commands.jsonl` 缺少实测 duration 而失败；未伪造历史耗时，PR 保持 draft。
- func-full、random、perf、Linux、Vivado implementation/bitstream 均未通过，不作完成声明。

## 风险与回退

- 后续整机 mismatch、BTB/RAS、LACC 和 release gates 仍未完成。
- 回退方式：revert 本迭代提交；不得修改或合并 `main`。

日志：`logs/refactor/20260714-0302-spinal-active-backend/`。代理不得自动创建、标记 ready 或合并 PR。
