# 20260713-2227-mem-active-overlay

- Status: implementation_in_review（提交前验证阶段）
- Branch / Base SHA / Head SHA: `refactor/20260713-2227-mem-active-overlay` / `da44b6dea9d3b5adefb583b2399f67e43913d372` / `9511dc5e78bac8f6aa7cc6ad3bf17b16caae74df`（待提交）
- Owner / Agent: Codex `/root`
- Selected boundary and selection reason: 将已完成隔离差分的 `mem_stage` replacement 接入活动 reachable overlay；它是 WB 后续可验证的最小依赖，不混入 IF/ID 或整机流水迁移。
- Golden reference and locked tool versions: `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/mem_stage.v`；chiplab `a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`；myCPU gitlink `aa3bde1f3e720e71c2c78d6b81930d797b810149`；Vivado 2023.2 ML Standard build 4029153；Scala 2.13.16 / SpinalHDL 1.14.2 / Verilator 5.020。
- Behavior contract: `docs/contracts/mem-stage.md`；49/49 legacy ports，保持 valid/flush、load/store、异常和 WB payload 的周期语义。
- Files changed: `reference/component-replacements/active-reachable.json`、`active-reachable.meta.json`、`docs/refactor/status.yml`、`tests/test_replacement_reachability.py`，以及本目录日志。
- Attempts and failures: WSL worktree 指针下 Windows pytest 失败（18 failed、14 errors），原因是 Windows Git 无法解析 `/mnt/d/...` gitdir；恢复 Windows 指针后同一测试为 323 passed、10 skipped。overlay 首次缺 `--replacement-spec`，第二次缺 doctor report，第三次被 dirty source fail-closed 拒绝；均记录在 `commands.jsonl`。
- Commands and gate results: replacement reachability 12/12 PASS；Scala 4/4 PASS；chiplab-doctor PASS；Vivado doctor PASS；Windows pytest 323/333 PASS（10 个既有平台 skip）；官方 overlay/smoke 尚未在 clean commit 上执行。
- Functional/performance/resource delta: 尚无官方 func 结论；不宣称性能、资源、Linux、随机 DiffTest 或 FPGA 通过。
- Residual risks: legacy core_top/Verilog 仍为活动后端；官方 `func_lab19` 基线已知在 `0x1c07c79c` 失败；混合 overlay 仍需 smoke；Claude bridge 缺少 `GEEKPIE_CLAUDE_API_KEY`。
- Rollback: revert 本迭代提交即可移除 `mem_stage` reachable replacement 与状态计数，不回滚他人分支。
- PR URL or awaiting state: `awaiting_pr`；提交后推送分支，不自动创建或合并 PR。
- Next unblocked candidates: clean-head diagnostic overlay/smoke；随后独立 IF/ID active overlay，不与本分支混合。
