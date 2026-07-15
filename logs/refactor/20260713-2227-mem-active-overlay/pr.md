# PR 草稿（不自动创建）

标题：`refactor: add Spinal memory stage to active replacement overlay`

状态：`awaiting_pr`。本分支仅允许通过人工评审后合入，代理不创建或合并 PR。

范围：把已完成 `mem_stage` 叶子差分的 replacement 加入锁定 `core_top` reachable overlay，并同步 12 项 reachability 合同与测试计数。

证据：见 `iteration.md`、`summary.json`、`commands.jsonl`。Scala、chiplab doctor、Vivado doctor、reachability 和恢复 Windows gitdir 后的 323/333 自动化测试通过；clean commit 的 diagnostic overlay 接受 12 个 replacement。官方 smoke 严格 FAIL：功能 0/1、253 个 DUT warning、373 个官方环境 warning，首个 mismatch 与 baseline 同为 `0x1c07c79c`。

限制：不声称 58/81 功能、随机 DiffTest、性能、Linux、Vivado implementation/timing 或完整 SpinalHDL 重构通过。已知 baseline `func_lab19` mismatch 仍需单独归因。

回退：revert 本分支提交即可移除 `mem_stage` active replacement。
