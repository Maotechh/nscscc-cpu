# 20260713-1415-icache-spinal

- Status: implementation_in_review
- Branch / Base SHA / Head SHA: `refactor/20260713-1415-icache-spinal` / `fb5a63fbb3c5378a0d99d6122c0cf66b89a332c5` / `65d183294d495bcc110c24dc565172dabacb7842`
- Owner / Agent: memory / icache_spinal
- Selected boundary and selection reason: AXI bridge 已有审计提交，I-cache 是解除 IF 到 AXI 集成阻塞的最短活动存储边界；本迭代只迁移 I-cache，不做性能优化。
- Golden reference and locked tool versions: `a158aa8:rtl/icache.v`; Scala 2.13.16、SBT 1.10.11、SpinalHDL 1.14.2、Verilator 5.020、Yosys 0.33、Vivado 2023.2。
- Behavior contract: `docs/contracts/icache.md`
- Files changed: `OpenLa500ICache.scala`、generator/spec、`icache_gate.py`、合同、replacement RTL/spec、Makefile、status 和日志。
- Attempts and failures: 首次生成因 Spinal 临时默认值双重赋值失败，删除默认驱动后 2/2 生成通过；首次差分路径遗漏 golden `tools.v`，修正 gate 后通过；官方 mixed smoke 仅为 diagnostic，wrapper 报告 candidate_locked=false/baseline_exact=false。
- Commands and gate results: doctor 19/19；Scala scalafmt/compile/test 4/4；generate 2/2；contract/port/lint/Yosys 全部 PASS；12,000 周期 golden/candidate 差分 0 mismatch，事务级负控在 cycle 7 检出；自动化测试 309/309。
- Functional/performance/resource delta: 未声明。
- Residual risks: golden 自身 func_lab19 在 `0x1c07c79c` 失败；CACOP 历史实现不改 tag；死 write 端口只有 2-state 兼容合同。
- Rollback: revert 本迭代 PR，恢复 golden `rtl/icache.v` overlay。
- PR URL or awaiting state: awaiting_push（不自动创建或合并 PR）；Claude bridge unavailable（缺少 `GEEKPIE_CLAUDE_API_KEY`）。
- Next unblocked candidates: D-cache、IF/cache typed adapter；func smoke 需在 committed head overlay 后补录。
