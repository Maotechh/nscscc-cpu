# 20260712-1600-mul-harness

- 状态：`draft`（Claude 审核桥凭据不可用；不得提升）
- 分支：`refactor/20260712-1600-mul-harness`
- Base SHA：`2cb5d0b3a01591eadc2a5e4e34b51f0404197550`
- 当前 Head：`dedf10544fb6a2270173616034f177d1c2dabcef`
- Owner / Agent：Codex
- 目标边界：`mul-golden-harness`

## 动态选择

ALU 叶子已完成模块级证据但 whole-CPU 仍失败。下一活动边界分析指向 `a158aa8:rtl/mul.v`；不过当前 `tools/alu_gate.py`、Makefile 和测试入口硬编码 `TARGET=alu`，没有可运行的 mul oracle。故本迭代只建立 fail-closed 的 mul harness prerequisite，不替换 RTL，不改变比赛实现。

## 选择理由与约束

- golden mul 是活动 `mycpu_top.v` 实例，边界窄但包含一拍采样、reset hold、signed/unsigned 乘法和 64-bit 结果。
- harness 必须先从锁定 golden 建立可执行合同，不能把现有 `Multiplier.scala` 的 32-cycle ready/valid 逻辑当作 golden。
- ALU 现有 gate 和证据必须保持兼容；不做性能优化、不改 cache/pipeline/AXI。

## 行为合同

- 锁定 golden：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/mul.v`，SHA256 `251d2bba3e659c294c9a004bbb2b542435fcfa0b0c1582cc1a7a3edca765a4c0`，6045 bytes。
- 顶层只允许 `mul_clk/reset/mul_signed/x/y/result` 六个端口；`reset=1` 是同步 hold，不是清零复位。
- 每个 `reset=0` 的上升沿采样 32-bit signed/unsigned 输入并在该沿后更新 64-bit result；首次 active edge 前不比较未知状态。
- 独立数学模型、固定 seed `0x158aa8`、32 个 directed + 4096 个 random；不把 candidate 或 DUT 输出当作 oracle。

## 已执行门禁

| 门禁 | 结果 | 证据 |
|---|---|---|
| `doctor` | PASS | `build/manual-doctor`（锁定 manifest、分支、Vivado 2023.2 均匹配） |
| `harness_schema` | PASS | `make mul-contract OUT_DIR=/tmp/nscscc-mul-make-contract` |
| `automation_tests` | PASS | `make test-automation`：167 PASS，9 个条件性 SKIP（既有平台条件） |
| `golden_mul_diff` | PASS | `make mul-golden-unit OUT_DIR=/tmp/nscscc-mul-make-unit`：4128/4128，0 mismatch/skip/warning |
| `claim_review` | BLOCKED | Claude job `7e4decbc2fae445995731dd648aa812d` 因凭据缺失在模型启动前失败；见 `reviews/` |

## 尝试与失败

1. 直接在 `/mnt/d/.../build` 编译时，Verilator 本身只有锁定的 golden `WIDTHEXPAND`，但 GNU make 报告挂载文件系统的 clock-skew warning。按 fail-closed 规则返回非零，没有把环境警告加入 waiver。
2. 改用 WSL 原生 `/tmp` 输出目录重跑，消除 clock-skew；同一锁定工具链和向量完整通过。该差异是构建环境证据，不是放宽 warning policy。
3. `python -I -m unittest tests.test_mul_diff ...` 不是本仓库的 discovery 入口而失败；随后使用约定的 `make test-automation` 正确执行并通过。

## 失败记录

本迭代开始时尚未运行实现命令；每次失败会追加到 `commands.jsonl` 和本文件。

## 文件与 claim 边界

本迭代只新增合同、golden runner、负例测试、Make 入口和证据日志；不替换 `rtl/mul.v`，不把同工作树中尚未提交的 Spinal candidate 文件算入本迭代。通过结果只支持“锁定 golden harness 与独立模型一致”，不支持 Spinal 等价、整机功能、性能、Linux、Vivado FPGA 或完全重构。

## 回退与后续

回退方式为 revert 本迭代提交；不改写 `main`。下一候选是独立 `mul-spinal` 分支，必须在本 prerequisite 审核/提交后，使用同一合同做精确端口、显式 `mul_clk` ClockDomain、candidate lint/static 和 cycle differential。

## PR 状态

`awaiting_push`，只允许 stacked Draft；不自动创建 PR、不标记 ready、不合并。Claude 原始事件、中文结论和本地测试审查均保存在 `reviews/`。
