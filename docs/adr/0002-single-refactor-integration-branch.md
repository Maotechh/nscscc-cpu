# ADR 0002：单一重构集成分支

- 状态：采用
- 日期：2026-07-14
- 决策者：维护者与自动化代理

## 背景

早期重构按模块建立了多个并行 `refactor/*` 分支。后续活动 `core_top` 集成线已经通过
cherry-pick、重写或后续修复吸收其中的实现，但部分旧分支头不是最新提交的 Git 祖先，容易让
协作者误判为功能遗漏，也增加继续开发时选择 base 的成本。

## 决策

从 `ce50a05c87baef28e0eabd95e5b2b27b6820a400` 建立并持续使用
`refactor/20260714-1650-consolidated-spinal` 作为唯一最新的 SpinalHDL 重构集成分支。

- 旧模块分支经内容、patch-id 和后续修复审计后，以显式 merge parent 收敛历史。
- 已被后续实现吸收或取代的旧分支只合并历史，不恢复旧工作树内容。
- 后续功能边界继续使用独立 iteration id、中文日志、合同、证据和可回退 commit，但不再为每个
  功能建立长期并行分支。
- 集成分支持续推送到远端，保持 Draft/awaiting PR；不得自动合并 `main`。
- 旧 refactor 分支只有在 tip、远端 tip 和本地额外提交均被集成 HEAD 吸收，且对应 worktree 干净后才能清理。清理前生成 ancestry 清单；任何未知或未提交改动都必须保留。

## 约束

这项决策只收敛开发线，不降低 `AGENTS.md` 的测试、证据、claim 审核和禁止自动 merge 规则。
同一公开 contract 仍只能由一个活动迭代修改。每个行为边界必须单独提交，失败证据必须写入
对应日志，不能用集成分支替代 PR 审核。

## 后果

协作者只需跟随一个最新分支，活动生成物、状态源和验证证据有单一前沿。代价是该分支会包含
多个连续 iteration；因此每次提交信息和 `logs/refactor/<iteration-id>/` 必须明确边界与回退点。

## 2026-07-14 清理决策

维护者明确要求只保留一个最新重构开发 fork。`eadf441` 已被只读审计确认包含全部已发现本地和远端 `refactor/*` tip 后，清理了 28 个干净旧 worktree、31 个本地旧 ref 和 26 个 GitHub 远端旧 ref。远端现在只保留 `refactor/20260714-1650-consolidated-spinal`。

根仓库旧 worktree 含 4 个来源未确认的未跟踪路径，按仓库契约保留，不删除、不切分支；它的旧本地 branch ref 也是当前唯一例外。后续开发、提交和推送只允许发生在本 ADR 指定的集成 worktree/branch。
