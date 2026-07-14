# 20260714-1845-refactor-prune

- Status: `draft`
- Branch / Base SHA / audited source HEAD: `refactor/20260714-1650-consolidated-spinal` / `eadf4415a94d890a09c382af215fd76f66ef1b54` / `eadf4415a94d890a09c382af215fd76f66ef1b54`
- Owner / Agent: Codex；独立只读 ancestry 审核代理
- Selected boundary and selection reason: `repository/refactor_ref_prune`。维护者要求优先收拢此前大量功能 fork，并确保 GitHub 只有一个最新重构开发分支。
- Golden reference and locked tool versions: Git object graph 与 `eadf441`；本轮不修改工具 lock。
- Behavior contract: `docs/adr/0002-single-refactor-integration-branch.md`
- Files changed: 仅 ADR、状态与迭代证据；没有 CPU 行为源码变化。
- Functional/performance/resource delta: 无；本轮不产生功能、性能或资源 claim。
- Rollback: 已删除 ref 的提交仍由集成分支可达。需要恢复时从 `eadf441` 历史按原名称重新建立 ref；不回滚或改写 `main`。
- PR URL or awaiting state: `awaiting_pr`；不自动创建或合并。

## 清理前只读审计

- 所有 33 个本地 `refactor/*` tip 都是 `eadf441` 祖先。
- 所有 27 个 GitHub 远端 `refactor/*` tip 都是 `eadf441` 祖先。
- `icache` 本地 tip 比同名远端多两个日志提交；本地和远端 tip 均已被 `eadf441` 吸收。
- 除根仓库旧 worktree 外，所有旧 worktree 都干净。
- 根仓库旧 worktree 有 4 个来源未确认的未跟踪路径，禁止删除、stash、reset 或切换分支。

## 执行结果

- 删除 28 个干净且已吸收的旧 worktree。
- 删除 31 个已吸收的本地旧 `refactor/*` ref。
- 删除 26 个已吸收的 GitHub 远端旧 `refactor/*` ref。
- 远端只剩 `refactor/20260714-1650-consolidated-spinal@eadf441`。
- 本地只剩集成分支，以及因未跟踪文件而受保护的根 worktree 旧 branch ref。
- `make test-automation` 运行 341 项并通过，测试框架报告 10 项预期 skip；命令整体退出码为 0。
- Windows 删除 `icache` worktree 时首次受长路径限制中断；Git 元数据已移除但目录残留。确认目标绝对路径、干净状态和 ancestry 后，使用 PowerShell/.NET 长路径前缀删除残留，再继续清理；未触及其他目录。

## 后续规则

后续功能边界仍使用独立 iteration id、日志、合同与 commit，但全部在同一集成 worktree/branch 串行推进，不再创建功能 fork。根 worktree 的未知文件继续保留，直到其所有者处理。
