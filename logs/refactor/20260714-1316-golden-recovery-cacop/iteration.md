# 20260714-1316-golden-recovery-cacop

- Status: `blocked`
- Branch / Base SHA / Review target: `refactor/20260714-1316-golden-recovery-cacop` / `13e0c8da423bb75ca848aada91c67738f22a60ab` / `b2a73c83f9d849c6f67828e8dcfdd39a620e00ed`
- Owner / Agent: Codex；CACOP gate 由独立子代理实现，主代理复核并重跑 clean-head/官方闭环
- Selected boundary and selection reason: `baseline_validation/cacop`。锁定 baseline 与活动 Spinal core 均在 `0x1c07c79c` 失败，先恢复可执行局部 oracle，避免在错误基线上扩大等价声明。
- Golden reference and locked tools: `d22c13c1ecbee7b0423b7e4f4616f24d98457f02` 仅作本迭代 CACOP oracle；全局 `team_golden_candidate` 保持 `a158aa8`；chiplab `a2e11b3`；SpinalHDL 1.14.2；Verilator 5.020；Vivado ML Standard 2023.2。
- Behavior contract: `docs/contracts/golden-recovery-cacop.md`
- Rollback: revert 本迭代提交；不修改或合并 `main`，不更新 `reference/manifest.lock`。
- PR: `awaiting_pr`，只维护草稿，不自动创建、标记 ready 或合并。

## 实现与定向差分

- I/D Cache 的 CACOP 从普通 `cacheHit` 排除。
- 删除 lookup 中 `requestCacop -> Idle` bypass 和 CACOP 立即 `dataOk`。
- D-cache 外层 `dataOk` 保持 `!(requestPreld || requestCacop)`，避免 cancel/op 重叠产生伪完成。
- 新 gate 固定 d22 和 d76/2ff/408 的 Git blob identity，不修改全局 manifest。
- SHA256 为 `0e0a39e59fedb1937bb49c94e62b8cf9d5c2ff2acead3f3e9402241d136b932c` / `ebf5f12a1be68a2951bf1cf5a27ff2536fc297db049f66d22ce443c4ee8b392a` 的候选 I/D Cache RTL分别以 461/497 拍与 d22 逐拍零 mismatch；10/10 仿真，候选 lockstep 958 拍，总执行 4790 拍，skipped 0。该 gate 未记录 source HEAD，不能把结果直接绑定为 `b2a73c8` 整机证据。
- 覆盖 mode 0/1/2/3、way 0/1、mode2 hit/miss、120 拍 `rd_rdy` backpressure、单拍失效、mode2 miss 保留命中和 dirty writeback。
- d76 ghost-hit、2ff lookup bypass、408 immediate-data-ok 三个负控均在 I/D 两侧被捕获。

机器证据：`evidence/cacop-directed.json`。此结果只支持所列定向轨迹，不支持完整 cache、整机、性能或系统 claim。

## 可复现生成修复

首次 clean `968712c` 的生成逻辑会把 Git HEAD 写入 RTL 头，导致提交生成物后 publish-check 必然失配。`GenerateCoreTopCompat` 已关闭 `headerWithDate` 和 `headerWithRepoHash`，并在 clean `b2a73c8` 上重跑：

- Scala：4/4 PASS，25 个 ScalaTest 全部通过。
- generate/package/publish：3/3 PASS，两次生成一致。
- package SHA256：`517005efedf63a705a94569688cef4e9333b8809a17e74556f5f20fb89907c57`。
- port-check：49 个端口 PASS。
- Yosys：PASS。
- strict lint：FAIL。最终摘要没有保留可独立复核的 warning 精确计数，因此不声明数量或类别分解。
- chiplab doctor：PASS；锁定 chiplab、工具版本与哈希匹配，Vivado 为 `D:/Xilinx/Vivado/2023.2`。

## 官方 func_lab19

使用 committed `b2a73c8`、锁定 chiplab `a2e11b3` 和 package `517005ef...907c57` 建立精确 diagnostic overlay；replacement 数为 2，overlay 后 DUT 校验 PASS，worktree 未发生非预期修改。

- planned/executed/passed/failed/skipped：`1/1/0/1/0`。
- 旧首错 `0x1c07c79c` 已越过，但测试仍为严格 FAIL。
- 新首错：NEMU 期望 PC `0x1c07cfcc`，DUT PC `0x1c07cfdc`。
- instructions / clocks：`173247 / 607326`。
- trace SHA256：`7bebde0afb200be8c538a19133ca1a2e8d959a7a5f7031ab84b7fe4bc48cafd3`。

对应循环为 `st.w@cfcc -> lu12i.w@cfd0 -> add.w@cfd4 -> addi.w@cfd8 -> bne@cfdc`。trace 显示第二轮后 `0x1c07cfdc` 重复提交，但本迭代没有可执行 branch harness，因此只记录症状，不宣称根因已证明。

## 尝试、失败与审核

1. 历史 diagnostic overlay 共执行 d22/d76/2ff/408 四个点。d22 功能 parser 通过，后三者均首错于 `0x1c07c79c`；四次顶层 strict gate 均失败。因此 `history_bisect` 只表示诊断分类完成，机器计数为 0 PASS / 4 FAIL。
2. clean `968712c` 暴露生成 RTL 内嵌 HEAD 的自引用问题；修复并在 `b2a73c8` clean commit 上确认可复现。
3. strict lint 仍因未批准 warning 失败，本迭代不以 waiver 或吞 warning 伪造 PASS；未保存精确计数证据，故不声明数量。
4. 官方 `func_lab19` 确实执行且 skipped 0，但在 `0x1c07cfcc` 失败。
5. Claude review job `8780b724cf5d4b599c906aaf68d34655` 已调用，bridge 因缺少 `GEEKPIE_CLAUDE_API_KEY` 终止。原始事件在 `reviews/claude-raw.md`，降级审查不得表述为 Claude 审核。

## 功能、性能与资源变化

本轮只恢复 CACOP 功能语义并修复生成可复现性，不做性能优化。未运行 perf20、Vivado synth/implementation/timing/bitstream，因此没有 cycles、Fmax、LUT/FF/BRAM 改善声明。58/81、random、U-Boot、Linux 和完整顺序等价也未执行。

## 残余风险与下一候选

- 当前 `func_lab19` 和 strict lint 都失败，分支不能 ready。
- CACOP 定向 PASS 不等于全 cache 或整机 PASS。
- 下一最小边界是 branch/predictor replay：先建立 fetch redirect、stall、BTB lookup-valid 和 commit sequence harness，再修复重复 `0x1c07cfdc`，随后重跑同一官方 smoke。
- 本迭代保留为 stacked branch 的基线；不创建或合并 PR。
