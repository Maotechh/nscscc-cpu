# 20260710-2026-baseline

- 状态：`blocked`，只能提交 Draft PR
- 分支：`refactor/20260710-2026-baseline-automation`
- Base SHA：`20cae5fd66391f4a1bccc1b87035be421039144b`
- Review / Source HEAD：`45043bd8a89b0e4dea3911ed609d128252f0319f`
- Owner / Agent：Codex；独立复审由只读 Codex 子代理执行，不是 Claude
- 目标边界：`baseline_validation`

## 选择理由

`a158aa8` 只是 team golden candidate。开始本轮时没有绑定固定 chiplab、工具链、DUT 文件集合、构建新鲜度和结果 parser 的可重放证据；candidate 未复测通过前，任何 Spinal 模块替换都缺少可信 oracle。本轮因此先建立最小官方 RTL 闭环并实测 candidate，不迁移新的 CPU 功能模块。

该选择不是固定阶段或百分比。它解除全部后续等价替换共同依赖，golden evidence 强于当前 Scala 实现，且变更主要局限于 automation/reference/test contract。

## 固定输入与行为合同

- chiplab：`a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`
- chiplab `IP/myCPU` gitlink：`aa3bde1f3e720e71c2c78d6b81930d797b810149`
- candidate：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`
- support header：`f89c604845d8092d0efe1cc700ccedee748d7a0b:mycpu.h`
- JDK/SBT/Scala/Spinal：`17.0.19 / 1.10.11 / 2.13.16 / 1.14.2`
- Python/Verilator/Yosys：`3.12.3 / 5.020 / 0.33`
- Vivado：`2023.2 SW Build 4029153`

完整版本、URL、下载资产和二进制 SHA256 在 `reference/manifest.lock`；Scala 426 项语义依赖在 `reference/scala-dependencies.lock.json`；行为合同在 `docs/contracts/baseline-validation.md`。bootstrap 仍属于 TOFU，当前工具闭包不是完整 hermetic 系统镜像。

## 实现与修改

1. 新增统一 doctor、golden export、隔离 overlay、官方 `func_lab19` smoke、证据校验和迭代 validator。
2. golden export 只接受 22 个锁定 Git blob，排除 `btb.v.bak`、`regfile_dual.v`、`store_buffer.v`；support 文件不能借 header 注入额外 HDL。
3. chiplab reference 保持只读；每次运行使用 Linux 文件系统上的隔离工作副本，并复验官方 tracked tree 与 DUT manifest。
4. smoke 清理全部可复用构建物，要求新鲜产物、明确 timeout、NEMU/DiffTest marker 和结果 parser；Make 返回 0 不能覆盖 mismatch。
5. configure/build/simulation 三份 raw log 均记录绝对 locator 与 SHA256；大日志、trace、可执行文件和工程不提交 Git。
6. Scala gate 使用锁定离线 SBT/Coursier/Ivy cache、独立源码 workspace、隔离 JVM home/tmp/JNA、fresh 编译计数和 ScalaTest XML 后验。
7. Verilator policy 拒绝禁止类最终 `-Wno-*`、`-f/-F/@` response file、`.vlt`、缺失 RTL/include、inline waiver、header waiver 和无法静态解析的宏 include。
8. 正式 Python evaluator 强制 `-I`；WSL Python 版本与 binary SHA 进入 doctor/overlay/smoke 指纹链。
9. 16 个既有 Scala 主文件做机械 scalafmt；唯一识别出的非格式变化是删除未消费的 `ALU.sub_result`。该结论经独立静态复审，但不是整核等价证明。
10. 新增当前 4-bit Scala ALU local directed smoke：12 个结果向量和 4 个 flag 断言；测试名称明确声明不是 golden equivalence。

## 尝试、失败与修复

- Windows checkout 会把 chiplab mode `120000` symlink 退化为文本；正式 reference 改为只读 `/opt/chiplab-reference`。
- 早期 smoke 曾出现 `tee` 吞掉 Verilator error、旧产物复用、额外 support HDL、官方 oracle 工作树污染和并发运行风险；均加入 fail-closed 检查和负测。
- 初版 evaluator 没有锁定实际 Python、Verilator engine/runtime、SBT launcher、JDK modules、GCC cc1/collect2 与 Scala dependency closure；本轮逐项绑定。
- 初版 Scala runtime 继承宿主 `user.home/tmp/JNA`，且长路径导致 SBT Unix socket 失败；现在每轮使用短 `/tmp/nsg-*`，XML 采证后验证并删除。
- 初版 warning policy 可被 response file、`.vlt`、跨行 waiver、include header 和宏 include 绕过；当前 59 项自动化正负测试覆盖这些路径。
- Claude 第一次请求带只读工具，被 responses backend 在模型启动前拒绝；第二次使用无工具自包含请求，又因缺少 `GEEKPIE_CLAUDE_API_KEY` 在模型启动前失败。两次均没有 Claude 正文。

### Final evidence rerun

发现旧 exact 目录曾被中断前遗留命令再次覆盖后，为消除外层命令来源歧义，新建唯一 `/tmp/nscscc-baseline-final-45043bd` 并重跑：

1. 第一次 overlay 因新目录没有 doctor report 返回 2；这是预期的 fail-closed 行为，没有被改写成成功。
2. `chiplab-doctor` 返回 0，44/44 检查通过。
3. overlay 返回 0，22-file candidate overlay 通过。
4. `rtl-smoke` 实际运行并返回 1；子命令虽均返回 0，parser 仍捕获功能差异和 warning policy 失败。
5. 同一 evidence root 下重跑 Scala gate，4/4 task 通过。

最终命令、退出码、耗时和证据路径见 `commands.jsonl`；只采用 final 目录报告，旧 exact 报告不再作为活动证据。

## Exact gate 结果

| Gate | planned | executed | passed | failed | skipped | 结论 |
|---|---:|---:|---:|---:|---:|---|
| Windows doctor | 19 | 19 | 19 | 0 | 0 | PASS，含 Vivado version probe |
| Python automation | 59 | 59 | 59 | 0 | 0 | PASS |
| Scala tasks | 4 | 4 | 4 | 0 | 0 | PASS，16+1 fresh，1 test |
| chiplab doctor | 44 | 44 | 44 | 0 | 0 | PASS |
| locked overlay | 1 | 1 | 1 | 0 | 0 | PASS，22 files |
| build integrity | 1 | 1 | 1 | 0 | 0 | PASS，六个新鲜构建产物 |
| compile warning policy | 1 | 1 | 0 | 1 | 0 | FAIL，644 warnings |
| `func_lab19` | 1 | 1 | 0 | 1 | 0 | FAIL at `0x1c07c79c` |
| 独立 Verilator lint + Yosys | 2 | 0 | 0 | 0 | 2 | 未执行；账本记为 skipped，不能用于闭环 |
| Claude claim review attempts | 2 | 2 | 0 | 2 | 0 | UNAVAILABLE，无模型正文 |
| experiment integrity audit | 1 | 1 | 0 | 1 | 0 | WARN，证据诚实但范围不足 |

Scala 报告绑定 `repo_head_sha=45043bd...`：scalafmt、fresh main compile `16/16`、fresh test compile `1/1`、1 个 ScalaTest succeeded，failed/canceled/ignored/pending/aborted 均为 0；426 项 dependency manifest 稳定，JVM runtime isolation 与 cleanup 后验通过。

chiplab doctor 绑定同一 HEAD、manifest 和 evaluator SHA。overlay 的 doctor SHA、manifest SHA 与 smoke 的输入 SHA 逐层一致；raw log 和构建/仿真 artifact locator/hash 由独立复审再核对。

官方 `func_lab19` 实际执行 `172552` 条指令、`602903` 周期。首差为 PC `0x1c07c79c` 的 `t0(r12)`：期望 `0x000006e2`、实际 `0x00000008`；`this_pc` 实际为 `0x1c07c7a4`。Verilator warning 共 644 条：DUT 280、官方环境 364。由此 candidate 不能提升为 golden truth。

## 诊断矩阵

旧的单 case、固定 seed 诊断见 `evidence/baseline-matrix.json`：`d22c13c` 的功能 parser 通过，而直接子提交 `d76ca40` 在相同位置失败；后者修改 cache cacop 命中条件。该矩阵只缩小调查范围，不证明完整根因，也不批准 `d22c13c` 为 golden truth。其余诊断 raw artifact 属于历史外部证据，不替代本轮 locked final run。

## Claim 审核

Claude required review 状态为 `unavailable`，详见 `reviews/claude-raw.md` 与 `reviews/claude-summary.json`。降级执行独立只读 hardening、Scala 语义边界和实验完整性复审；这些报告只能收紧 claim，不能冒充 Claude 或解除 required check。

允许的最宽声明是：本 PR 建立并加固了锁定 baseline 验证闭环，并在 `45043bd` 对应 evaluator 下诚实复现 `a158aa8` 的单一官方 smoke 失败。不得据此声明 Scala/openLA500 等价、整核重构完成或任何未执行 gate 通过。

## 功能、性能与资源影响

本轮没有修改活动 golden CPU 行为，也不宣称性能或资源改善。58/81、random、20 项 perf、U-Boot、Linux、独立 rtl-static/Yosys 与 Vivado synth/implementation/timing/bitstream 均未执行；原因是最小 locked smoke 与 warning policy 已失败。

Vivado 只确认 `D:/Xilinx/Vivado/2023.2` 的 launcher/binary SHA、2023.2 与 SW Build 4029153；未证明许可证、器件、Fmax、LUT/FF/BRAM、DRC 或 bitstream。

## 残余风险与阻塞

- `a158aa8` 的 cacop 路径在 locked smoke 中失败，当前没有可直接用于等价替换的 golden truth。
- 644 条 warning 尚未逐文件修复或建立有效 waiver；不得全局关闭规则。
- Scala 源的格式化和有限 ALU test 不具备整核行为等价证据。
- bootstrap 仍是 TOFU；系统 headers、glibc、动态链接器、GCC/Python 完整闭包未完全锁定。
- Claude required review 不可用。
- 高层功能、随机、性能、系统与 FPGA release gate 仍无证据。

## 回退

本轮通过 revert Draft PR 回退。官方 reference、工具链、chiplab worktree 和大 artifact 不在源码仓库；禁止 reset、改写 `main`、放宽 oracle 或删除 reference。`main` 与 `origin/main` 保持 `20cae5f`。

## PR 与下一候选

evidence-only commit 已创建，但普通 `git push -u origin refactor/20260710-2026-baseline-automation` 因 GitHub 443 连接超时失败，且没有建立 upstream。当前状态为 `awaiting_push`；网络恢复后只能普通 push 并创建 Draft PR，代理不得 merge。`pr.md` 保留完整离线草稿，不能用直接提交主分支替代 PR。

下一最小候选是独立 `golden-recovery/cacop` 迭代：只恢复 `d76ca40` 引入的活动 cache cacop 行为，补 directed test，并重跑 doctor、overlay、warning、官方 smoke 与必要回归。baseline 恢复并重新审计前，不开始大范围 Spinal 模块替换。
