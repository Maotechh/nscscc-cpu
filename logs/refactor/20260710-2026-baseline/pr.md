# Draft PR：建立并加固可复现的 openLA500 baseline 验证闭环

## 状态

Draft，当前 `awaiting_push`。首次普通 push 因 GitHub 443 连接超时失败，未建立 upstream；`gh` 也没有登录态。网络/认证恢复后仍只允许创建 Draft PR。本 PR 不允许代理自动合并；`main` 和 `origin/main` 均保持 `20cae5fd66391f4a1bccc1b87035be421039144b`。

## Base / Source Head / 日志

- Base：`20cae5fd66391f4a1bccc1b87035be421039144b`
- Review / Source Head：`45043bd8a89b0e4dea3911ed609d128252f0319f`
- Branch：`refactor/20260710-2026-baseline-automation`
- 日志：`logs/refactor/20260710-2026-baseline/`
- PR Head：本日志所在 evidence-only commit；由 PR 平台与 `git rev-parse HEAD` 给出，不在提交内容中自引用哈希

## 目标与动态选择理由

锁定的 `a158aa8` 没有官方环境复测通过证据，不能直接作为 Spinal 重构 oracle。本 PR 只建立 fixed-reference、candidate overlay、Scala gate 和官方 `func_lab19` 证据闭环，并诚实记录 candidate 失败；不替换 cache、流水线或 AXI。

该边界解除后续所有替换的共同阻塞，golden evidence 可执行且 blast radius 限于自动化、版本锁与有限测试，因此优先于任何 CPU 模块迁移。

## 行为合同

见 `docs/contracts/baseline-validation.md`。Make 返回 0、Scala 生成成功或 Verilator build 成功都不能单独构成功能 PASS；`SKIP`、timeout、未批准 warning 和 DiffTest mismatch 均保持失败。

## 主要修改

- 锁定 chiplab/gitlink、candidate、工具、Vivado、SBT/Scala/Spinal、Python evaluator 和语义依赖 hash。
- 建立 22-file golden allowlist、support 来源、只读 reference 与 Linux 隔离 overlay。
- 增加构建新鲜度、官方 tree/DUT manifest、NEMU/DiffTest parser、raw log hash、并发锁和安全清理。
- 增加 isolated/fresh Scala format/compile/test gate、426-artifact offline cache、JVM runtime 后验和 Verilator warning bypass 负测。
- 增加 59 个 Python 自动化测试与当前 4-bit ALU 的有限 directed smoke。
- 机械格式化既有 Scala 主源码；唯一识别出的非格式变化是删除未消费的 `sub_result`。没有整核等价 claim。

## Gate 结果

| Gate | planned | executed | passed | failed | skipped | 结论 |
|---|---:|---:|---:|---:|---:|---|
| Windows doctor | 19 | 19 | 19 | 0 | 0 | PASS，Vivado 仅 version/build/binary |
| Python automation | 59 | 59 | 59 | 0 | 0 | PASS |
| Scala tasks | 4 | 4 | 4 | 0 | 0 | PASS，16+1 fresh，1 test |
| chiplab doctor | 44 | 44 | 44 | 0 | 0 | PASS |
| locked overlay | 1 | 1 | 1 | 0 | 0 | PASS，22 files |
| build integrity | 1 | 1 | 1 | 0 | 0 | PASS，六个新鲜产物 |
| compile warning policy | 1 | 1 | 0 | 1 | 0 | FAIL，644 warnings |
| `func_lab19` | 1 | 1 | 0 | 1 | 0 | FAIL at `0x1c07c79c` |
| 独立 Verilator lint + Yosys | 2 | 0 | 0 | 0 | 2 | 未执行，不能满足 rtl-static |
| Claude claim review attempts | 2 | 2 | 0 | 2 | 0 | UNAVAILABLE，无模型正文 |
| experiment integrity audit | 1 | 1 | 0 | 1 | 0 | WARN，范围不足且 baseline 失败 |

`func_lab19` 执行 `172552` instructions / `602903` cycles。首差：`t0` expected `0x000006e2`、actual `0x00000008`；`this_pc` actual `0x1c07c7a4`。详细报告、三个 raw log locator/SHA 和构建 artifact SHA 在 `evidence/rtl-smoke-summary.json`。

## Claim 边界

- 支持：分支/base/main 状态；锁定 reference/tool 的 doctor；22-file overlay；candidate 在该单一官方 smoke 的精确失败数字。
- 限定支持：Vivado 只完成安装版本 probe；Scala 只完成构建和当前 4-bit ALU local directed smoke；d22/d76 只作单 case 诊断。
- 不支持：Scala/openLA500 等价、整核重构完成、rtl-static、58/81、random、perf、Linux、Fmax/LUT/FF/BRAM 或 FPGA flow 完成。

Claude bridge 两次均在模型启动前失败，不能称为 Claude 已审核。独立 Codex 只读复审只用于收紧 claim，不能解除 required check。

## 性能、资源、系统与 FPGA

未运行 perf、U-Boot、Linux 或 Vivado synth/implementation/timing/bitstream，没有周期改善、Fmax 或资源 claim。当前周期数只是失败 smoke 的定位数据，不是性能结果。

## Contract / 配置 / 许可证 / 提交包

- `core_top` 外部合同：未改变，也未由 Scala 实现。
- CPU 配置：未改变活动 golden Verilog；Scala 配置仍不具备历史行为合同。
- 许可证：overlay 保留上游许可证；reference 只提交 manifest/hash，不提交大仓或工具链。
- 生成物：大日志、波形、工作副本、可执行文件和工程不提交，locator/hash 写入报告。
- 提交包：未生成；本 PR 不是 release candidate。

## 风险与回退

主要阻塞是 `a158aa8` cacop 功能失败、644 条 warning、rtl-static 未执行和 Claude bridge unavailable。回退方式是 revert 本 Draft PR；不得改写主分支、放宽 oracle 或删除 reference。

后续只在独立 `golden-recovery/cacop` 分支/PR 恢复该行为并补测试。本 PR 未合入时，dependent PR 必须锁定 base SHA 并保持 Draft；任何代理都不得自动 merge。
