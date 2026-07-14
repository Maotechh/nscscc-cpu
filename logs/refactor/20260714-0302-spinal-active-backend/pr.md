# Draft PR: 激活纯 SpinalHDL openLA500 backend

- Iteration: `20260714-0302-spinal-active-backend`
- Base: `78efdf97b6208da3806fcbc02dca69061284d3b7`
- State: awaiting_next_push / draft

## 行为合同

- 纯 Spinal `core_top` 的 49 个官方端口和 `TLBNUM=32` 保持不变。
- `CommitEvent` 延迟一拍，GPR/CSR `ArchState` 保持实时，匹配 golden NBA/DPI 观察顺序。
- `DIFFTEST_EN` 下实例化官方七个 DPI 模块；综合配置不保留未解析 DPI 依赖。
- TLBFILL index 使用 CSR `rand_index`；GPR0 和 EUEN 强制为 0。

## 当前验证

- Scala 4/4 PASS，24 tests PASS；双次生成可复现。
- package SHA256：`748b025cedac922dbf6ff2707b61e6e230138b091c89ebe778b0eede446dea41`。
- 49/49 端口、Yosys hierarchy/check、发布一致性 PASS。
- 官方 `DIFFTEST_EN` 静态链接退出 0，但仍有 warning。
- 严格 Verilator lint FAIL：88 条未批准 warning。
- `210f596` 的旧官方 smoke 在 600.054 秒后超时且观察到 0 条提交；本提交的 adapter 尚待新 overlay 复测。
- func-full、random、perf、Linux、Vivado implementation/bitstream 均未通过，不作完成声明。

## 风险与回退

- debug breakpoint 下不复现 golden 的重复 level 事件；当前实现优先满足 commit 不重不漏不变量。
- BTB/RAS、LACC、性能计数和整机等价仍未完成。
- 回退方式：revert 本迭代提交；不得修改或合并 `main`。

日志：`logs/refactor/20260714-0302-spinal-active-backend/`。代理不得自动创建、标记 ready 或合并 PR。
