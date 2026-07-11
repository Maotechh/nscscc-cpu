# Baseline 自动化最终加固复审

- 日期：2026-07-11
- 审查对象：`45043bd8a89b0e4dea3911ed609d128252f0319f`
- Base：`20cae5fd66391f4a1bccc1b87035be421039144b`
- 分支：`refactor/20260710-2026-baseline-automation`
- 外部证据：`/tmp/nscscc-baseline-exact-45043bd`
- 审查性质：独立 Codex 只读 hardening 与 claim 复审
- 身份声明：**本文件不是 Claude 审核，不能替代 `claude-review` gate**
- 总体结论：**BLOCKED / DRAFT**。exact 证据链可信，自动化加固的两个上一轮 HIGH 已关闭；但锁定候选功能失败、Verilator warning gate 失败、迭代账本仍过期，且 Claude review 不可用。因此不得把本分支标记为 Ready，不得合并到 `main`，也不得开始基于 `a158aa8` 的等价替换。

## Blocker 与 High

### B1. 锁定 candidate 仍未建立 golden baseline

`func/func_lab19` 的三个官方命令均返回 0，fresh build integrity 为 PASS，但 NEMU DiffTest parser 明确判定功能失败：

```text
instructions = 172552
clocks       = 602903
first PC     = 0x1c07c79c
t0 expected  = 0x000006e2
t0 actual    = 0x00000008
this_pc actual = 0x1c07c7a4
```

报告同时记录 `difftest_mismatch`、`trace_error`，没有 good trap、END by Syscall 或 reached-test-end marker。准确测试对象是 `a158aa8` 的 22 个锁定 RTL、`f89c604:mycpu.h` 与锁定官方 chiplab 环境的组合；它不能升级为 golden truth。

### B2. Verilator compile warning gate 失败

报告记录 644 条 Verilator warning，其中 DUT 280、官方环境 364；`verilator_compile_status=warning`、`verilator_compile_counts.failed=1`。`build_integrity_status=pass` 只表示模型和软件镜像为本次 fresh build 且没有已识别 build error，不等于 warning gate、独立 lint 或 `rtl-static` PASS。

### B3. 当前迭代账本仍不可提交

仓库自带 validator 实跑结果：

```text
python -I tools/refactor.py validate-iteration \
  --iteration-dir logs/refactor/20260710-2026-baseline
ERROR: summary.head_sha must be a non-empty string
```

当前仍存在以下过期材料：

- `summary.json` 的 `head_sha` 为 null，C6 仍错误声称没有 Scala 测试。
- `artifacts.json` 仍索引旧 `/tmp/nscscc-final-evidence`，没有索引 exact-45043bd 文件。
- `commands.jsonl` 仍是旧 schema、旧命令和旧测试计数。
- `evidence/git-state.txt` 仍写 `source_head_sha=916ad146...`。
- `evidence/func-lab19-excerpt.md` 仍引用 exact-916ad14 的 raw log。
- `pr.md`、`iteration.md` 与 `docs/refactor/status.yml` 尚未完成 exact-45043bd 对齐。

在这些文件更新并通过 validator 前，`logs/` 和 `docs/refactor/` 只能保持未跟踪的 Draft evidence，不能作为 PR 完成材料。

### B4. Claude claim review 仍不可用

已有 Claude job 在模型启动前因 provider credential 缺失而失败。该事实只能记录为 `unavailable`；本次独立 Codex 复审不能冒充 Claude，也不能解除 `claim_review` blocker。

### High 结论

本轮对 `45043bd` 源码和 exact 报告未发现新的 HIGH 级证据完整性缺陷。上一轮两个 HIGH 已关闭，见后文。对 d22/d76 的诊断若被扩展为完整回归或根因证明，仍属于不允许的 HIGH 级夸大 claim。

## Exact 证据重算

### Doctor -> overlay -> smoke 哈希链

现场重算结果：

```text
chiplab-doctor.json          80be582143397f6088724866ef70a9f43fb529cbdd4c87e781793ef0a1a0e4f3
chiplab-overlay-manifest     3c6976c675b0e4f69abff9f7a5192f1d7390e4cefc683be0ec3cf054f994c4c7
chiplab-overlay.json         d21e2c563c0bdb81d75f7af22ad4b6cccd32caef9e0a216d1f8e2d40581c5873
rtl-smoke.json               9fd2a03161ccf15bbb2c6827775ba6fdd5e6517bd273ca7239d66e1ec824b90a
scala-check/summary.json     fb500718df2815447efac10d35c0bc0e7436bb8a884346209049b3e49d461ae5
```

复制到 `evidence/` 的 doctor、overlay manifest、overlay report、RTL smoke 和 Scala summary 与上述外部文件逐字节一致。doctor 直接记录 `repo_head_sha=45043bd...`；overlay manifest、overlay report 与 smoke 通过 doctor/report SHA 逐层绑定。`tools/refactor.py` evaluator SHA 为 `de2c6e0b...`，`tools/scala_gate.py` evaluator SHA 为 `8e5b695c...`，均与 HEAD 文件一致。

Doctor 共 44/44 checks PASS，包括：

- chiplab `a2e11b38...` 与 myCPU gitlink `aa3bde1...`；
- ext4/symlink 和官方 reference clean；
- Python 3.12.3 binary SHA `1643dacd...`；
- 锁定的 GCC/cc1/collect2、NEMU、picolibc、QEMU、SBT、Java、Verilator 与 Yosys 指纹。

### Raw log 绑定

最终 `rtl-smoke.json` 只引用 run id `1783720663485039720-156500`。现场 SHA 与报告逐项一致：

```text
01-configure.log   88d0d2b3bea4d22c370a255b232d9a1fe6037cbc0a1b785d84411e4f51bd6e2f
02-build.log       125784d46bf2ea7bb6fdbc56e1f3408bd7db77feb62cb7f2b852371a0c3a15ee
03-simulation.log  e1d3835eacfb099e9e8742f099544edd5d4de41edf97dd5aa88129ab422e89c3
```

同目录中较早的 run `1783720530991862410-154451` 没有被最终报告引用；本次结论不混用其 simulation log。

### Scala 与自动化

exact Scala summary 记录：

- format、compile、test-compile、test：4/4 PASS，0 fail，0 skip；
- fresh compile：16 个 main source、1 个 test source；
- ScalaTest：1 total、1 succeeded，其余 outcome 全为 0；
- source/config stable、dependency cache stable、JVM home/tmp/JNA isolation PASS；
- Verilator policy PASS，扫描 2 个实际 RTL，未发现 response file、VLT、全局禁止 suppression、inline waiver、missing include 或 unresolved include；
- 当前测试是 4-bit ALU local directed smoke，不是 golden differential equivalence。

`evidence/automation-tests.txt` 记录 59/59 PASS；本次复审再次执行 `make test-automation`，同样为 59/59 PASS。

## 上一轮 High 的关闭情况

### H1. RTL evaluator Python provenance：已关闭

`tools/refactor.py` 强制 `python -I`，并把 `sys.executable` 纳入 installed tool fingerprint。exact doctor 对 Python binary SHA 和 `Python 3.12.3` version 都实际执行并通过；该 fingerprint 随 doctor SHA 进入 overlay/smoke 链。

### H2. Header/macro include waiver 闭包：已关闭

Scala warning policy 会递归扫描字面量 include closure；missing header 直接失败。凡 `include` 不能静态解析为单个字面量文件名，包括宏展开形式 `` `include `HEADER``，都会进入 `unresolved_include_directives` 并令 gate 失败。对应负向测试已纳入 59 项自动化测试。

该实现对不能证明安全的 include 采取 fail-closed，而不是猜测宏展开结果。exact ALU RTL 没有 include，报告中 `unresolved_include_directives=[]`。

## Claim 判定

| Claim | 判定 | 允许范围 |
|---|---|---|
| C1 分支/base/main 未被修改 | SUPPORTED | HEAD 为 `45043bd...`；main、origin/main、merge-base 均为 `20cae5f...` |
| C2 锁定 chiplab/tool 环境 | SUPPORTED WITH SCOPE | exact doctor 44/44 PASS；不等于 Vivado synth、许可或完整 hermetic OS closure |
| C3 22-file candidate overlay | QUALIFIED | 22 个 allowlist RTL、f89 header、官方 LICENSE 来源可追溯；只证明三个已知 dead/backup 文件未纳入，不是完整 hierarchy reachability 证明 |
| C4 locked candidate 功能失败 | SUPPORTED | 数字、PC、寄存器 mismatch、raw logs 与 parser 一致；不能成为 golden truth |
| C5 d22/d76 首坏边界 | DIAGNOSTIC ONLY | 仅一个 case、固定 seed、每 commit 一次旧诊断；不能证明完整回归、具体 cache 行的因果性或批准 d22 为 golden |
| C6 Scala baseline | QUALIFIED | exact HEAD 上 4/4 task、16+1 fresh compile、1 个 local ALU smoke PASS；不支持 CPU/流水线/golden 等价 claim |

## 未执行 Gate

以下没有 PASS 证据：

- 独立 Verilator `--lint-only -Wall` 与 Yosys hierarchy/check；
- `core_top` port/contract；
- 58 赛用功能集、81 通用功能集；
- random NEMU DiffTest；
- 20 项 perf；
- U-Boot、Linux；
- Vivado synth、implementation、timing、resource、bitstream；
- clean-clone release gate；
- Claude review。

`rtl-smoke.json` 已正确写明 `rtl_static_gate=not_executed_by_rtl_smoke`。Vivado 2023.2 安装/version/hash probe 不能替代 FPGA gate。

## 当前允许的最窄 Claim

> 在 source HEAD `45043bd8a89b0e4dea3911ed609d128252f0319f`、锁定 chiplab `a2e11b38...`、锁定工具指纹和 ext4 overlay 环境中，22-file `a158aa8` candidate 与 `f89c604:mycpu.h` 的 `func_lab19` fresh RTL smoke 实际执行并失败：172552 instructions、602903 cycles，首个 DiffTest mismatch 位于 PC `0x1c07c79c`。同一 exact HEAD 的 Scala format/compile/test 4/4 PASS，自动化单元测试 59/59 PASS；Scala 测试仅为当前 4-bit ALU local directed smoke。该证据支持继续修复 baseline 和自动化，不支持 golden、完全重构、完整回归、Linux 或 FPGA 完成 claim。

## 下一步门槛

1. 先把 summary、commands、artifacts、git-state、失败摘录、PR 草稿和 status 全部更新到 exact-45043bd，并通过 `validate-iteration`。
2. 保持 PR 为 Draft/blocked；不得把本复审当作 Claude PASS。
3. 先建立可通过的 golden baseline 或单独修复已定位的 cacop 回归，再开始任何等价模块替换。
4. 不自动合并到 `main`。
