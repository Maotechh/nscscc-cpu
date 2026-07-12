# 20260712-1651-mul-spinal

- 状态：`draft / implementation_in_review`
- 分支：`refactor/20260712-1651-mul-spinal`
- Base SHA：`a17b30165a70f2eae37a6f7074f5fbf7a25ee688`
- 当前 Head：`a17b30165a70f2eae37a6f7074f5fbf7a25ee688`（实现提交前）
- Owner / Agent：Codex
- 目标边界：`mul`

## 选择理由

前置迭代已经把活动 `a158aa8:rtl/mul.v` 的六端口、一拍采样、同步
reset-hold 与 signed/unsigned 64-bit 数学语义锁为可执行 harness。`mul` 依赖已满足、
边界窄且 golden evidence 强，本轮只迁移该叶子，不修改 decode、pipeline、cache、CSR、
AXI 或性能策略。分支 stacked 在未合并的 harness 分支上，只允许 Draft，不创建或合并 PR。

## 行为合同与实现

合同见 `docs/contracts/mul.md` 与 `reference/component-contracts/mul.json`。

- 新增 `openla500.execute.OpenLa500Mul` 与独立生成器。
- `mul_clk` 建立显式 ClockDomain；`reset` 是同步 hold，不初始化结果寄存器。
- 每个 `reset == 0` 上升沿捕获完整 64-bit signed/unsigned 乘积。
- 生成模块精确为 `mul`，只有六个历史端口，无隐式 `clk/resetn`。
- 生成 RTL 为 1260 bytes，SHA256
  `5ff75243dd504bf74c01645862364cd416dffc554d64c82dea6be8f7181660d6`。
- replacement spec 只替换 `rtl/mul.v`，base SHA256 为
  `251d2bba3e659c294c9a004bbb2b542435fcfa0b0c1582cc1a7a3edca765a4c0`。

自动化新增 locked dependency cache 前后复核、Windows worktree Git 指针的 WSL 映射、
RTL gate 输入快照和 source/snapshot 结束复核。static/formal 摘要同时记录 HEAD、manifest、
evaluator 与 Yosys/Verilator 版本和二进制哈希。

## 尝试与失败

1. Windows `core.autocrlf=true` 把 `reference/scala-dependencies.lock.json` 物化为 CRLF，
   SHA `f3c1a62a...` 与锁定 LF SHA `0a5b155c...` 不同；正式 Scala/生成门禁改在 WSL
   原生 LF clone 运行，未放宽 lock。
2. 第一轮 Scala test 有两个链式正则语法错误；修正后 compile/test 通过但 scalafmt 失败，
   使用锁定 scalafmt 3.8.3 格式化后才重新取得 4/4 PASS。
3. 首次聚焦 unittest 误用模块导入方式，3 个 import error；改用 discover 后暴露
   Windows `.git` 指针在 WSL 中无法解析，修复并增加回归。
4. 完整 golden Booth/Wallace 对直接乘法的顺序形式等价未获证明：flattened SAT、capture
   lemma、`equiv_induct`、ABC DSEC/CEC/ACEC 均在 75--180 秒超时；bit0 可证但高位无结论。
   一次错误的 clock extraction 会把 DFF 优化为 undef，负控也错误等价，已丢弃。
5. candidate formal 改为 first-capture-aware 2-state 合同证明并加入两项负控；它不是
   golden RTL 形式等价，不能据此提升为 `differential_pass`。
6. 独立审查发现生成 gate 未复算 dependency cache、static/formal 存在 RTL TOCTOU、摘要
   缺工具/HEAD provenance；均已修复，并分别补负例。
7. Vivado 首次命令把 `-log/-journal` 放到 `-tclargs` 后，参数计数错误并返回 2；修正后
   两个 `synth_design` 均完成。candidate 仍有 63 条未批准 warning，严格 gate 失败。
8. pre-commit `evidence-check` 因 review target 尚未提交且缺 Claude 审查文件而按 schema
   返回 2；未创建占位审查绕过校验。该检查必须在实现提交、commit-bound 门禁和真实审查后重跑。
9. 独立终审发现 candidate unit 直接编译源路径仍存在 change-and-restore TOCTOU 窗口，
   且 contract 结果未绑定 evaluator bytes；已改为只编译 `OUT_DIR/input/mul.v` 哈希快照，
   同时复核源/快照并记录 canonical contract evaluator SHA。终审还发现若干预提交命令记录
   与原始 artifact 不一致，最终日志必须从原始 summary 修正，不能沿用这些命令。

## Pre-commit 门禁

以下结果验证当前源码快照，但报告中的 repository HEAD 仍是 base `a17b3016`；实现提交后
必须重新运行，不能作为最终 commit-bound 证据。

| Gate | 结果 | 摘要 |
|---|---|---|
| Windows doctor | PASS | Vivado 2023.2 ML Standard launcher/binary/hash/version 匹配 |
| chiplab doctor | PASS | chiplab `a2e11b3`、myCPU gitlink、工具链与包校验匹配 |
| Python automation | PASS | 192/192，0 skip |
| Scala | PASS | format/compile/test-compile/test 4/4 |
| contract | PASS | golden blob、六端口与时序合同匹配 |
| elaborate | PASS | 1/1，RTL SHA `5ff75243...` |
| generate | PASS | 2/2 字节一致；426 个依赖 artifact 前后稳定 |
| port / lint / Yosys | PASS | 精确六端口；Verilator 0 warning；Yosys check 通过 |
| cycle differential | PASS | 32 directed + 4096 random = 4128/4128；4127 perturb；32 reset-hold |
| candidate contract formal | PASS | temporal induction + 2 个必须失败的负控，3/3 |
| golden formal equivalence | OPEN | 多种 solver 流程超时，无证明也无反例 |
| chiplab mixed smoke | PENDING | 只能在提交过的 source/spec HEAD 上运行 |

## Vivado 2023.2 叶子诊断

器件固定为 `xc7a200tfbg676-2`，只运行 `synth_design`，不是 implementation/bitstream。

| 项目 | Golden | Candidate |
|---|---:|---:|
| LUT | 1537 | 50 |
| FF | 592 | 34 |
| DSP | 0 | 4 |
| BRAM | 0 | 0 |
| synth warning | 3 | 63 |

candidate 的 62 条 `Synth 8-3332` 与 DSP PREG 分解/裁剪相符，但没有 waiver。叶子没有
input/output delay，WNS 为 `inf`，因此不得声明 Fmax；DPIP/DPOP DRC 也保持公开。该项只能
声明“综合完成并记录资源”，严格 warning gate 为 FAIL。

## Claim 边界与残余风险

当前只允许在实现提交后复测成功时声明：提交的 Spinal-generated `mul` 可复现、端口匹配，
通过独立数学模型 cycle differential 与 candidate 2-state 时序合同证明。不得声明 golden
完整形式等价、整机功能通过、`integrated_pass`、性能/Fmax、58/81、random DiffTest、Linux
或 FPGA 闭环通过。

残余阻塞：committed mixed overlay/smoke、Claude claim review、Vivado 63 条 warning，以及
golden 高位算术 formal solver timeout。官方 baseline 已知在 `func_lab19@0x1c07c79c` 失败；
mixed 若复现相同失败也只能作为诊断观察。

## 回退、PR 与下一候选

回退方式为 revert 本迭代提交，并继续使用 `a158aa8:rtl/mul.v`。PR 状态
`awaiting_implementation_commit`；不自动创建、标记 ready 或合并。

实现提交与 mixed 诊断收口后，自动选择器将重新检查活动边界；优先考虑可建立强 golden
harness 的下一个窄叶子，不把性能优化混入 Spinal 功能重构。
