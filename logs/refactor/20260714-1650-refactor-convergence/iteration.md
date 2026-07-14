# 20260714-1650-refactor-convergence

- Status: `draft`
- Branch / Base SHA / Head SHA: `refactor/20260714-1650-consolidated-spinal` / `ce50a05c87baef28e0eabd95e5b2b27b6820a400` / 待收敛提交
- Owner / Agent: Codex；两个独立只读子代理审计分支 ancestry 与活动源码缺口
- Selected boundary and selection reason: `repository/refactor_branch_convergence`。维护者要求先把既有并行重构成果收敛到唯一最新开发线，避免继续按单个功能建立长期 fork。
- Golden reference and locked tool versions: 当前工作树 `ce50a05`；工具版本继续使用 `reference/manifest.lock`，本迭代不更新 lock。
- Behavior contract: `docs/adr/0002-single-refactor-integration-branch.md`
- Files changed: 待最终填写。
- Attempts and failures: 目标系统的旧 goal 处于 blocked 且工具不允许原地修改 objective；实际执行优先级已按维护者最新指令切换，本项不伪装为 goal tool 更新成功。
- Commands and gate results: 待执行分支图、内容一致性、Scala/自动化和证据门禁。
- Functional/performance/resource delta: 本轮只收敛 Git 历史和开发策略，设计工作树不得变化；不产生性能或资源 claim。
- Residual risks: 旧分支可能包含已被后续修复取代的实现，禁止普通 content merge 覆盖当前活动源码。
- Rollback: revert 历史收敛提交和日志提交；不改写旧分支或 `main` 历史。
- PR URL or awaiting state: `awaiting_pr`；不得自动创建或合并。
- Next unblocked candidates: 完成 64-entry/2-bit/RAS predictor；补齐官方 func/random/perf/fpga wrapper。

## 初始事实

- `ce50a05` 已包含 ALU、mul/div、core_top、流水级、CSR/TLB/地址转换、I/D Cache、AXI、
  Commit/DiffTest 活动路径及随后 CACOP/forwarding/BTB replay 修复。
- 多数旧分支是 `ce50a05` 祖先；非祖先分支需要逐项证明其活动源码已相同或被后续 commit 取代。
- 本轮不删除旧分支、不改变 `main`、不创建 PR。
