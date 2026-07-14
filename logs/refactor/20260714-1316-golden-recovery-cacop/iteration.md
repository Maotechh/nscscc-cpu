# 20260714-1316-golden-recovery-cacop

- Status: `implementation_in_review`
- Branch / Base SHA / Head SHA: `refactor/20260714-1316-golden-recovery-cacop` / `13e0c8da423bb75ca848aada91c67738f22a60ab` / 待本轮提交
- Owner / Agent: Codex；CACOP gate 由独立子代理实现，主代理复核并重跑
- Selected boundary and selection reason: `baseline_validation/cacop`。锁定 baseline 与活动 Spinal core 均在 `0x1c07c79c` 失败，先恢复可执行 oracle，避免继续在错误基线上扩大等价声明。
- Golden reference and locked tool versions: `d22c13c1ecbee7b0423b7e4f4616f24d98457f02` 仅作为本迭代 CACOP oracle；全局 `team_golden_candidate` 保持 `a158aa8`；chiplab `a2e11b3`；SpinalHDL 1.14.2；Verilator 5.020；Vivado ML Standard 2023.2。
- Behavior contract: `docs/contracts/golden-recovery-cacop.md`
- Rollback: revert 本迭代提交；不修改或合并 `main`，不更新 `reference/manifest.lock`。
- PR: `awaiting_pr`，仅维护草稿，不自动创建、ready 或合并。

## 历史定位

固定 chiplab diagnostic overlay 实际执行了四个历史点，均为 `planned=1/executed=1/skipped=0`：

| 提交 | 功能 parser | 指令 / 时钟 | 首个分歧 | 严格 gate |
|---|---|---:|---|---|
| `d22c13c` | PASS | 174059 / 609660 | 无 | FAIL，存在未批准 Verilator warning |
| `d76ca40` | FAIL | 172559 / 602471 | `t0@0x1c07c79c`: `0x6e2` / `0x8` | FAIL |
| `2ffb1ab` | FAIL | 172559 / 602464 | 同上 | FAIL |
| `40830b8` | FAIL | 172559 / 602464 | 同上 | FAIL |

因此只允许声明“在已测试序列中，d76 是 d22 后首个复现该功能回归的点”。不能把 d22 的 functional parser PASS 写成严格 smoke PASS。

## 实现与定向差分

- I/D Cache 的 CACOP 从普通 `cacheHit` 排除。
- 删除 lookup 中 `requestCacop -> Idle` bypass 和 CACOP 立即 `dataOk`。
- D-cache 外层 `dataOk` 保持 `!(requestPreld || requestCacop)`，避免 cancel/op 重叠产生伪完成。
- `tools/cacop_recovery_gate.py` 固定 d22 及 d76/2ff/408 的 Git blob identity，不读取或修改全局 manifest。
- 候选 I-cache 461 拍、D-cache 497 拍与 d22 逐拍零 mismatch；10/10 仿真检查、4790 总仿真拍，skipped 0。
- 覆盖 mode 0/1/2/3、way 0/1、mode2 hit/miss、120 拍 `rd_rdy` backpressure、16 次单拍失效、4 次 mode2 miss 保留命中和 6 次 D-cache dirty writeback。
- d76 ghost-hit、2ff lookup bypass、408 immediate-data-ok 三个负控均在 I/D 两侧被 gate 捕获。

机器证据：`evidence/cacop-directed.json`，原始编译/trace 保留在 `build/cacop-directed-gate-v4/`。

## 尝试与失败

1. clean `968712c` 的 Scala、49 端口和 Yosys 通过，但完整 `make generate TARGET=core_top` 在 publish-check 失败。fresh 与 tracked RTL 只差 Spinal 自动写入的 `// Git hash`，形成“提交生成物后 HEAD 再变化”的自引用闭环。
2. 已在 `GenerateCoreTopCompat` 关闭 `headerWithDate/headerWithRepoHash`。锁定 Scala gate 4/4 通过，新 RTL 两次生成可复现，且包内不再含仓库 HEAD；本修改提交后需重新发布 tracked RTL 并从 clean commit 再跑 publish-check。
3. clean `968712c` 严格 lint 为 FAIL：86 条未批准 warning（84 `UNUSEDSIGNAL`、1 `UNUSEDPARAM`、1 `DECLFILENAME`）。端口和 Yosys 通过不覆盖该失败。
4. 首次 PowerShell/WSL 包装错误解析 `$((END-START))`；另一次把 OUT 错展开到 `/scala-check`。两次结果均作废，未进入 evidence。

## 当前门禁

| Gate | 结果 | 证据 |
|---|---|---|
| doctor + Vivado 2023.2 probe | PASS | `evidence/doctor.json` |
| history localization | PASS（定位任务）；四次 strict smoke 均 FAIL | 本文件及外部原始结果 locator |
| CACOP d22 directed lockstep | PASS，10/10 | `evidence/cacop-directed.json` |
| Scala after header fix | PASS，4/4 | `evidence/header-fix-scala.json` |
| core_top generate/package after header fix | 子步骤 PASS；tracked publish 尚未更新 | `evidence/header-fix-generate.json`、`header-fix-package.json` |
| port / Yosys | PASS / PASS | `evidence/clean-head-port-968712c.json`、`clean-head-yosys-968712c.json` |
| strict lint | FAIL，86 warnings | `evidence/clean-head-lint-968712c.json` |
| current committed head official smoke | 待执行 | 待生成 |
| claim review / experiment audit | 待执行 | 待生成 |

## 功能、性能与资源变化

本轮只恢复 CACOP 功能语义并补验证，不做性能优化。尚未执行 perf20、Vivado synth/implementation/timing/bitstream，因此没有 cycles、Fmax、LUT/FF/BRAM 改善声明。

## 残余风险与后续候选

- 定向 958 拍不能替代完整 cache 随机 backpressure、全流水提交序列或整机顺序等价。
- 需要在稳定生成头部提交后重新发布完整 `mycpu_top.v`，从 clean head 跑 generate/publish/port/Yosys/lint 和官方 `func_lab19`。
- 若当前 head 越过 `0x1c07c79c`，下一项才是扩大功能集；若未越过，继续用首个新 mismatch 定位，不把问题归因于性能。
