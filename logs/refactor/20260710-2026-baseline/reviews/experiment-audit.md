# 20260710-2026-baseline 实验完整性审计

- 审计日期：2026-07-11
- 审计对象：`45043bd8a89b0e4dea3911ed609d128252f0319f`
- 证据目录：`logs/refactor/20260710-2026-baseline/evidence/`
- 审计身份：独立只读 Codex 子代理（本报告写入除外）
- 独立性限制：**这不是 Claude 审核，也不是 GPT-5.4 或其他模型家族的 cross-model 审核**。`experiment-audit` skill 要求的跨模型独立性本轮未满足；本报告只能作为同模型家族的独立证据复核，不能替代 AGENTS.md 要求但当前不可用的 Claude review。

## 总体结论：WARN

当前 final-45043bd 证据没有发现 phantom result、伪造 oracle、自归一化分数或数字篡改。最终报告、原始日志和构建产物的哈希链可重放，关键数字与原始输出一致。

但被测 `a158aa8` 的唯一官方 smoke **实际失败**，Verilator warning policy 也失败；验证范围只有一个 `func_lab19`、一个固定总线延迟 seed，以及一个有限 Scala ALU directed smoke。独立 rtl-static/Yosys、58/81、random、perf、U-Boot/Linux 和完整 Vivado FPGA flow 均未执行。因此证据完整性可接受，功能结论为 FAIL，项目完成度结论仍为未完成。

## 1. 证据链复核

### 1.1 固定输入与 evaluator

- 当前分支为 `refactor/20260710-2026-baseline-automation`，当前源码 HEAD 为 `45043bd...`；`main`、`origin/main` 均为 `20cae5f...`。
- `tools/refactor.py` SHA256 为 `de2c6e0b...a33cd`，与 chiplab doctor、overlay、smoke 中的 evaluator hash 一致。
- `tools/scala_gate.py` SHA256 为 `8e5b695c...68978`，与 Scala summary 一致。
- `reference/manifest.lock`、`golden-rtl-files.lock`、`scala-dependencies.lock.json` 的 SHA256 分别为 `743dd7e5...2f20`、`da1bc6d4...c8db`、`0a5b155c...51d`，均与报告绑定值一致。
- 相关 tracked 输入与 `HEAD` 一致；Scala summary 记录的 21 个源文件均与当前文件的 size/SHA256 一致，before/after/source snapshot hash 均为 `9a9f5c1f...ea89`。

证据：`evidence/chiplab-doctor.json:277`、`evidence/chiplab-overlay-manifest.json:189`、`evidence/scala-summary.json:234`。

### 1.2 report、raw locator 与 artifact

- 重新比较 WSL 原报告与 Git 证据副本：chiplab doctor、overlay report、overlay manifest、RTL smoke、Scala summary 共 5 份，全部逐字节相同。
- 重新访问并计算报告中所有唯一 locator：3 份 smoke command raw log、9 个 RTL 构建/仿真 artifact、4 份 Scala task log、7 个 Scala 仿真 artifact、1 份 ScalaTest XML，共 24 项；24/24 存在且 SHA256 匹配。带 size 声明的 16 项为 16/16 匹配。
- `artifacts.json` 当前 14 个索引项逐一复算，path、SHA256、size 为 14/14 匹配。
- 三份 smoke raw log SHA256 分别为 `88d0d2b3...6e2f`、`1ed5642e...b7ff`、`4db7d5dd...4975`，对应 configure/build/simulation，见 `evidence/rtl-smoke-summary.json:110`、`:124`、`:136`。
- raw artifact 位于 WSL `/tmp`，当前仍可访问且 hash 匹配，但它不是长期归档。若 `/tmp` 被清理，Git 中只剩摘要与 hash，无法再审阅完整 trace；正式 PR/CI 应补持久 artifact locator、保留期和内容 hash。

### 1.3 DUT 与官方环境来源

- 22 个 candidate 文件的 source Git blob、golden export copy 与 `IP/myCPU` overlay copy 逐项复算，hash/size 均为 22/22 匹配。
- `mycpu.h` 与 `f89c604...:mycpu.h` 匹配；LICENSE 与 `aa3bde1...:LICENSE` 匹配；overlay marker 与 immutable overlay manifest 均为 `86e0a230...c917`。
- `/opt/chiplab-reference` 当前 clean，HEAD 为 `a2e11b38...`，`IP/myCPU` gitlink 为 `aa3bde1...`；隔离 worktree 只显示预期的 myCPU overlay 和两个 marker。
- 这里的 `45043bd` 是 evaluator/source HEAD；实际被测 CPU 是锁定的 `a158aa8` 22-file candidate 加两个支持文件，不能把该 smoke 解释为当前 Scala CPU 的系统测试。

证据：`evidence/chiplab-overlay-manifest.json:2`、`:3`、`:191`；`evidence/rtl-smoke-summary.json:97`、`:181`。

## 2. 关键数字复核

### 2.1 Doctor 与自动化

- Windows doctor：19/19 pass。Vivado 仅验证 launcher/binary hash、`2023.2` 和 `SW Build 4029153`；probe 没有保存 raw log（`log_path`/`log_sha256` 为 null），未验证许可证、器件或 FPGA flow。证据：`evidence/windows-doctor.json:152`、`:154`、`:168`。
- chiplab doctor：44/44 pass，绑定 `repo_head_sha=45043bd...`。证据：`evidence/chiplab-doctor.json:277`、`:279`。
- Python 自动化记录为 59/59 pass；本审计又以 `python -I -B -m unittest discover -s tests -v` 现场复跑，仍为 59/59 pass。证据文件本身记录 `Ran 59 tests`：`evidence/automation-tests.txt:62`。

### 2.2 Scala gate

- 4/4 tasks pass、0 failed、0 skipped；fresh compile 为 16 个 main source、1 个 test source，ScalaTest 仅 1 个 test succeeded。task log 和 XML hash 均已复算。证据：`evidence/scala-summary.json:6`、`:232`、`:316`、`:559`、`:585`、`:611`、`:637`。
- 唯一测试在 `spinal/src/test/scala/openla500/ALUSpec.scala:37` 明确标为 local smoke；实际只有 12 个结果向量（`:65-80`）与 4 个 flag 断言（`:66`、`:69`、`:83-84`）。它不是与 `a158aa8:rtl/alu.v` 的 differential test，也不覆盖整核。

### 2.3 官方 `func_lab19`

- configure、build、simulation 三个子命令均 exit 0，且没有 timeout；这只证明命令完成，不能证明功能通过。
- 结果 parser 正确判定 FAIL：`172552` instructions、`602903` clocks；首差为 PC `0x1c07c79c` 的 `t0(r12)`，NEMU/right 为 `0x000006e2`，DUT/wrong 为 `0x00000008`；DUT `this_pc` 为 `0x1c07c7a4`，末尾为 `Both Error(Code:0x700)`。
- 原始 simulation log 同时确认已加载锁定 NEMU 且 `Difftest enabled`；没有 good-trap、END-by-syscall 或 reached-test-end marker。
- Verilator compile raw log 重新计数为 644 条 warning，其中 DUT 280、官方环境 364，`%Error` 为 0。build integrity 为 PASS，但 compile warning policy 与最终 gate 均为 FAIL。

证据：`evidence/rtl-smoke-summary.json:96`、`:110-140`、`:142-148`、`:177`、`:218`、`:228-239`、`:254`。

## 3. Experiment-audit 检查

### A. Oracle 来源：PASS

功能 oracle 来自锁定 chiplab 的官方 NEMU DPI DiffTest 和 simulator termination marker，不是从 DUT 输出生成的伪 ground truth。`a158aa8` 只是 DUT candidate；本次失败反而证明 evaluator 没有把 candidate 自己当 oracle。

### B. 分数归一化：PASS

没有用 DUT 自身 max/min/mean 归一化的评分。报告的是原始指令数、周期数、warning 数和首个寄存器/PC mismatch；IPC `0.286202` 也未被当作性能 PASS 或相对提升。

### C. 结果存在性与数字一致性：PASS（保留期 WARN）

当前 final evidence、原报告、24 个唯一 raw/artifact locator 和 14 个 artifact index 项全部存在且 hash/size 一致。simulation raw 中的数字逐项匹配 summary。风险仅在 `/tmp` artifact 缺少长期保留保证，不构成当前 phantom result，但会降低未来可审计性。

### D. 执行路径与 phantom gate：PASS

报告没有把 Make exit 0、Scala elaboration 或 Verilator build 误报为功能 PASS。未运行的 gate 明确记为未执行/unsupported；没有发现用 dead metric 或手写 PASS 文本替代当前 final smoke parser 的情况。

### E. 范围充分性：WARN

实际范围为一个官方 case、一个固定 seed、一次 locked candidate run，以及一个 12-vector/4-flag Scala ALU local smoke。该范围足以支持“精确复现此处失败”和“自动化入口可执行”，不足以支持 golden truth、Scala/Verilog 等价、完整 RTL 闭环或完全重构。

### F. 评估类型

- RTL smoke：`official_reference_difftest`，锁定 NEMU reference model + simulator markers。
- Scala ALU：`directed_local_smoke`，手写期望向量，不是 golden differential。
- Vivado：`installation_version_probe_only`，不是 FPGA evaluation。

## 4. Claim 审核

| Claim | 判定 | 审计结论 |
|---|---|---|
| C1 分支/base/main 状态 | supported | 当前 Git 状态与 evidence 一致；main 未合并。 |
| C2 锁定 doctor 与 22-file overlay | supported | source/export/overlay 与 report 链逐项匹配；注意被测 DUT 是 `a158aa8`，不是 Scala core。 |
| C3 `a158aa8` 的 exact `func_lab19` 失败数字 | supported | raw simulation 直接支持 172552/602903、PC/t0/this_pc mismatch。 |
| C4 Scala gate 4/4 与有限 ALU smoke | supported_with_qualification | 只支持 format/compile/test 和 1 个 local test，不支持 ALU/整核等价。 |
| C5 Vivado 2023.2 probe | supported_with_qualification | 只支持安装版本/build/binary；其 raw probe log 未归档，且不支持许可、器件、综合、实现、时序或 bitstream。 |
| C6 d22/d76 cacop 诊断 | supported_with_diagnostic_scope | matrix 只支持单 case/固定 seed 的回归定位；不能证明完整根因或批准新 golden。 |
| C7 broad completion claim | unsupported | 当前证据明确反对 rtl-static/full regression/Linux/FPGA/完全重构完成声明。 |

## 5. 未执行或未通过项

- 未通过：compile warning policy；官方 `func_lab19`。
- 未执行：独立 Verilator lint、Yosys hierarchy/check、58 项、81 项、random DiffTest、多 seed/随机 backpressure、20 perf、U-Boot、Linux。
- Vivado 未执行：synthesis、implementation、timing、resource、DRC、bitstream；也未验证 license/device availability。
- 未证明：`core_top` Scala 兼容合同、Scala/Verilog module diff、CommitEvent/官方完整 DiffTest contract、完全 Spinal 重构。
- Claude 两次调用均在模型启动前失败；本报告不是跨模型替代品。

## 6. 审计后的最宽安全声明

> 在 source HEAD `45043bd8a89b0e4dea3911ed609d128252f0319f` 对应的锁定 evaluator、chiplab `a2e11b38...` 和工具指纹下，`a158aa8` 22-file candidate 的单一 `func/func_lab19` fresh smoke 被实际执行并失败：172552 instructions、602903 cycles，首个 DiffTest mismatch 位于 PC `0x1c07c79c`；同一 HEAD 的 Scala gate 4/4 和 Python automation 59/59 通过，但 Scala 测试仅为有限 local ALU smoke。该证据不支持 golden truth、RTL 完整回归、Scala 等价、Linux/FPGA 或完全重构完成。

## 7. 后续动作

1. 保持迭代 `blocked`、PR 为 Draft，不合并 main。
2. 在独立 golden-recovery/cacop PR 中修复可见回归，并至少重跑 locked smoke 与相关 directed test。
3. 单独执行并归档 Verilator lint/Yosys；不能用 smoke compile warning 列表代替 rtl-static gate。
4. 将 raw log/trace/构建产物迁移到有 URL、SHA256、size 和 retention 的持久 CI artifact。
5. Claude bridge 恢复后补 required cross-model claim review；在此之前不得把本报告表述为 Claude/GPT-5.4 审核。
