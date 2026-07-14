# 20260714-1650-refactor-convergence

- Status: `draft`
- Branch / Base SHA / reviewed merge SHA: `refactor/20260714-1650-consolidated-spinal` / `ce50a05c87baef28e0eabd95e5b2b27b6820a400` / `09cfa96a1b67e2f5764b1ab015e3e51d307558fa`
- Owner / Agent: Codex；两个独立只读子代理审计分支 ancestry 与活动源码缺口
- Selected boundary and selection reason: `repository/refactor_branch_convergence`。维护者要求先把既有并行重构成果收敛到唯一最新开发线，避免继续按单个功能建立长期 fork。
- Golden reference and locked tool versions: 当前工作树 `ce50a05`；工具版本继续使用 `reference/manifest.lock`，本迭代不更新 lock。
- Behavior contract: `docs/adr/0002-single-refactor-integration-branch.md`
- Files changed: ADR 0002、收敛日志和结构化证据；`09cfa96` 只增加旧分支 merge parent，不改变 tracked tree。
- Attempts and failures: 目标系统的旧 goal 处于 blocked 且工具不允许原地修改 objective；实际执行优先级已按维护者最新指令切换，本项不伪装为 goal tool 更新成功。第一次直接在移动后的 Windows worktree 中从 WSL 运行 Scala gate，WSL Git 无法解析 `.git` 内的 Windows 绝对 gitdir，退出 1；见 `evidence/attempt-1-wsl-moved-worktree.json`。随后从已推送 `09cfa96` 建立只读 clean clone 重跑通过。
- Commands and gate results: merge 前后 tree 均为 `c06788dbf5d96baaa5ddd5311c6cead87d3ab4ec`；60/60 个本地/远端 refactor ref 均成为 merge HEAD 祖先；Scala 4/4、ScalaTest 25/25、Python automation 341/341 PASS。Claude bridge 已调用但因缺少 `GEEKPIE_CLAUDE_API_KEY` 在 reviewer 启动前失败。
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

## 收敛结论

- 使用 `ours` strategy 收敛 11 个最大旧分支头；旧 AXI 分支已由旧 ICache 分支覆盖。
- merge 前后 `git diff --exit-code` 为 0，因此不会回退 DiffTest、forwarding、CACOP 或 BTB replay。
- `refs/heads/refactor` 与 `refs/remotes/origin/refactor` 共扫描 60 个 ref，非祖先数量为 0。
- 两名独立只读子代理均确认 `ce50a05` 未遗漏旧分支的活动 CPU 实现；意见原样摘要见 `reviews/`。
- Claude Job `b0a97b665ce7495096c5f2e694c7de6a` 没有 reviewer 响应，本轮保持 Draft。
