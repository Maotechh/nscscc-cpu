# 独立只读 Claim 审核

审核方式：独立只读代理；未修改源码。Claude bridge 因环境变量缺失未返回响应，本文件不是 Claude 审核。

## 结论

- 阻塞：diagnostic overlay 和 func smoke 均不可作为 gate PASS；253 条 DUT warning 未逐条 waiver。
- 阻塞：58/81、random DiffTest、多 seed、perf20、U-Boot/Linux、Vivado implementation/timing/bitstream 和顺序形式等价均未执行。
- 阻塞：Claude `GEEKPIE_CLAUDE_API_KEY` 缺失，PR 只能保持 draft/awaiting_pr。
- 允许的最窄表述：`a874bd9` 的 clean diagnostic overlay 接受 12 个 committed replacement，其中 `mem_stage` blob 与叶子差分 SHA 一致；单一 `func_lab19` trace SHA、指令/周期计数及首错与锁定 baseline 相同，因此仅说明未观察到更早可见分歧。该运行严格 FAIL，不构成功能通过、集成完成或顺序等价证明。

## 证据核对

- overlay：`evidence/chiplab-overlay.json`，clean=true，12 replacements，chiplab/myCPU lock 匹配。
- reachability：`evidence/reachability.json`，`rtl/mem_stage.v -> mem_stage`，selected_count=12。
- smoke：`evidence/rtl-smoke.json`，configure/build/simulation 原生 rc=0，严格 parser 0/1，首错 PC `0x1c07c79c`，instruction 172552，trace SHA `8efa7942...38acb`。
- baseline 对照：`../20260710-2026-baseline/evidence/rtl-smoke-summary.json`；必须双边引用，不能把单边报告当作“相同”证明。
