# 20260712-1651-mul-spinal

- 状态：`draft / implementation_in_review`
- 分支：`refactor/20260712-1651-mul-spinal`
- Base SHA：`a17b30165a70f2eae37a6f7074f5fbf7a25ee688`
- Review target / 已测试 Head：`f6c55e6dcb42761c283febf99460214452628fd0`
- 首个实现提交：`dea1b95f13dbefaa185255c206a962c6d210b203`
- 远端：`origin/refactor/20260712-1651-mul-spinal` 已推送；未创建 PR
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
10. 首个实现提交两次推送分别因 HTTPS connection reset 和 443 暂时不可达失败；未强推或
    改写历史。加固提交 `f6c55e6` 后第三次推送成功。
11. 最终 locked candidate 和 committed mixed 的官方 `func_lab19` 均执行到同一既有
    DiffTest 首错；两侧还分别有 644/640 条未批准 warning，因此 smoke 严格 gate 均失败。
12. 第一项 Claude job 因 responses backend 禁止 reviewer tools 在模型启动前失败；已保留
    原始错误，并用内嵌完整 diff、禁用 tools 的第二个 job 重试，不能把 bridge 错误计为审查。
13. 第二项 Claude job 因缺少 `GEEKPIE_CLAUDE_API_KEY` 在模型启动前失败；experiment-audit
    代理随后因平台 usage limit 无法完成修正后复核。当前 schema/evidence-check 已 PASS，
    但审查状态仍是 `unavailable / pending external recheck`。
14. 首次 evidence publication push 和随后 `ls-remote` 精确查询均被 GitHub connection
    reset；tracking ref 仍停在 `f6c55e6`，因此没有把含糊的 `Everything up-to-date`
    当成远端成功证据。尚未推送的 publication commit 在补齐记录后 amend，再重试 fast-forward。

## Commit-bound 本地门禁

以下结果全部来自 WSL 原生 LF clean clone `/tmp/nscscc-mul-f6c55e6-src` 或同一
`f6c55e6` 的 Windows clean worktree。紧凑索引见 `evidence/local-gates.json`。

| Gate | 结果 | 摘要 |
|---|---|---|
| Windows doctor | PASS | Vivado 2023.2 ML Standard launcher/binary/hash/version 匹配 |
| chiplab doctor | PASS | chiplab `a2e11b3`、myCPU gitlink、工具链与包校验匹配 |
| Python automation | PASS | 193/193，0 skip |
| Scala | PASS | format/compile/test-compile/test 4/4 |
| contract | PASS | golden blob、六端口与时序合同匹配 |
| elaborate | PASS | 1/1，RTL SHA `5ff75243...` |
| generate | PASS | 2/2 字节一致；426 个依赖 artifact 前后稳定 |
| port / lint / Yosys | PASS | 精确六端口；Verilator 0 warning；Yosys check 通过 |
| cycle differential | PASS | 4128/4128，0 skip；编译 hash snapshot；4127 perturb；32 reset-hold |
| candidate contract formal | PASS | temporal induction + 2 个必须失败的负控，3/3 |
| golden formal equivalence | OPEN | 多种 solver 流程超时，无证明也无反例 |
| golden formal equivalence | OPEN | solver 超时，无证明也无反例；不计入 candidate formal PASS |

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

## 官方 chiplab 诊断

环境锁定为 chiplab `a2e11b3`、myCPU gitlink `aa3bde1`。candidate 使用 baseline
overlay；mixed 只从提交 `f6c55e6` 替换 `rtl/mul.v`，replacement SHA 为
`5ff75243...`，状态为 diagnostic、`gate_eligible=false`。

| 项目 | Candidate | Mixed |
|---|---:|---:|
| 执行 / skip | 1 / 0 | 1 / 0 |
| 功能结果 | FAIL | FAIL（diagnostic） |
| instructions / cycles | 172552 / 602903 | 172552 / 602903 |
| 首错 | `0x1c07c79c`，t0 expected `0x6e2` actual `0x8` | 相同 |
| trace SHA256 | `8efa7942...` | `8efa7942...` |
| warning | 644 | 640 |

两侧 configure、build、simulation 子命令均为 0，且 artifact fresh、post-run DUT verification
通过；但功能 oracle 和 warning policy 失败，所以 wrapper 正确返回 1。该结果只支持“一项
失败诊断观测一致，mixed 少 4 条 DUT warning”，不支持功能或集成 PASS。完整索引见
`evidence/chiplab-comparison.json`。

## Claim 边界与残余风险

当前仅允许声明：提交的 Spinal-generated `mul` 可复现、精确匹配端口，通过独立数学模型
cycle differential 与 candidate 2-state 时序合同证明；以及单一失败的 `func_lab19`
candidate/mixed 诊断观测一致。不得声明 golden 完整形式等价、4-state X/Z 等价、整机功能
通过、`integrated_pass`、性能/Fmax、58/81、random DiffTest、Linux 或 FPGA 闭环通过。

残余阻塞：`func_lab19@0x1c07c79c` 既有失败、mixed 640 条未批准 Verilator warning、
Vivado candidate 63 条未批准 warning、golden 高位算术 formal solver timeout，以及尚在
收口的独立 claim review。因此状态保持 `implementation_in_review`，不能提升为
`differential_pass` 或 `integrated_pass`。

## 回退、PR 与下一候选

回退方式为 revert 本迭代提交，并继续使用 `a158aa8:rtl/mul.v`。PR 状态
`awaiting_pr / draft only`；分支已推送，但不自动创建、标记 ready 或合并。

动态选择器已确认下一最小边界应先建立活动 `a158aa8:rtl/div.v` 的 golden harness，再在
独立迭代迁移 `OpenLa500Div`；现有根目录 `Divider.scala` 协议不兼容，不能当作进度。
