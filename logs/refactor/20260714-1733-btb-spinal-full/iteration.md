# 20260714-1733-btb-spinal-full

- Status: `draft / implementation_in_review`
- Branch / Base SHA / Head SHA: `refactor/20260714-1650-consolidated-spinal` / `cc8e1f30fd27272849d65e0858873c5d2e15f1a3` / `eadf4415a94d890a09c382af215fd76f66ef1b54`
- Owner / Agent: Codex；另有独立只读 predictor 审核
- Selected boundary and selection reason: `predictor/full_btb_ras`。旧活动 backend 只有 32-entry always-taken 临时实现，与锁定配置和 a158 的 64-entry/2-bit/RAS 意图不一致，是当前 fetch 路径中最大的明确缺口。
- Golden reference and locked tool versions: `a158aa8:rtl/btb.v` 仅作为行为意图候选，不作为天然 truth；JDK 17.0.19、Scala 2.13.16、SpinalHDL 1.14.2、Verilator 5.020、chiplab `a2e11b38...`。
- Behavior contract: `docs/contracts/predictor.md`
- Files changed: 新增独立 `OpenLa500Predictor` 与定向 ScalaTest；活动 `SpinalCoreBackend` 接入 typed lookup/update `Flow`；`CoreConfig` 将 16 项 return-site matcher 与 8 深度 return stack 分离；发布并同步生成 `mycpu_top.v` 和三份 replacement manifest。
- Functional/performance/resource delta: 本轮不做性能优化；未执行 Vivado，因此不声明 Fmax、LUT、FF 或 BRAM 变化。
- Rollback: revert `508fe52` 与 `eadf441`，回到 `cc8e1f3`；不改写主分支历史。
- PR URL or awaiting state: `awaiting_pr`；不自动创建 PR，不自动合并。

## 行为合同与实现范围

- 64-entry 全相联 BTB，完整 PC tag 匹配。
- 2-bit 饱和计数器；strongly-untaken 项不预测 taken。
- 16-entry JIRL/return-site matcher 与 8 深度运行时 return stack。
- invalid、delete、target correction、6-bit LFSR replacement 与 RAS 优先策略。
- 更新使用完整 PC 重匹配，不沿用 a158 中有宽度缺陷的 5-bit index 更新路径。

这是一项对 a158 可辨识设计意图的修正实现。完整 PC 更新、delete 生效、64 项可访问、当前拍 strongly-untaken 选择和 RAS 冲突优先级均可能与 a158 逐周期行为不同，因此不得声明顺序或逐周期等价。

## 尝试与失败

1. 首次 SBT 命令的 `Test / testOnly` 参数格式错误，测试没有执行。
2. 首次 predictor 仿真被 5 个 `UNUSEDSIGNAL` warning 拒绝；未放宽 warning policy，而是修改存储和测试观测。
3. 第二次仿真在 testbench 再次拉高隐式 reset 后停在 Verilator eval；调用方 184 秒超时，随后用 `jstack` 定位并显式终止孤立进程。
4. `508fe52` clean clone 的首次 `make generate` 正确拒绝 stale tracked package；`eadf441` 随后同步发布 RTL 与三份 manifest。
5. 最终 strict `make lint` 失败。首批类别包括 `DECLFILENAME`、`UNUSEDPARAM`、`UNUSEDSIGNAL`；其中新 backend 的 `decode_io_btb_index` 未消费，其他为既有 perf/AXI/cache/TLB 等未使用信号。没有添加全局 waiver。
6. 最终 mixed diagnostic smoke 的功能 parser 通过，但总 gate 因 251 条 DUT warning 和 364 条官方环境 warning 失败。
7. Claude job `526788a2475c47a4b377d215e5ab3443` 在 reviewer 启动前因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败；该结果不能表述为 Claude 已审核。

## 门禁结果

| Gate | 结果 | 证据与边界 |
|---|---|---|
| predictor directed | PASS | 1/1，seed `0x158aa8`，`evidence/predictor-directed.json` |
| scala-check | PASS | `508fe52` 上 4/4 task、26/26 ScalaTest、skipped=0；`508fe52..eadf441` 没有 Scala/build 源变化，`evidence/scala.json` |
| generate/package/publish | PASS | 两次生成一致；原始 RTL `1b9340cd...`；发布包 `07a2a2d9...` |
| core-top contract | PASS | 49 ports、`TLBNUM=32`、无 legacy backend |
| port-check | PASS | `evidence/port-check.json` |
| Yosys | PASS | 零 warning，`evidence/yosys-check.json` |
| replacement reachability | PASS | `evidence/replacement-reachability.json` |
| chiplab doctor | PASS | 锁定 reference/tool 检查通过 |
| strict lint | **FAIL** | warning policy 非零退出，`evidence/lint.json` |
| mixed `func_lab19` | 功能路径 PASS；总 gate **FAIL** | 174069 instructions、609803 clocks、DiffTest library loaded、到 syscall、无 first mismatch；`good_trap=false`、UART 不作为该 case oracle、warning policy 失败，`evidence/rtl-smoke.json` |
| func-58 / func-81 / random | 未执行 | 仓库尚无统一 target，不能计为 skip PASS |
| perf / system / Vivado | 未执行 | 不产生相关 claim |
| Claude claim review | 不可用 | bridge 缺少 API key；已降级为独立只读审查 |

## 允许与禁止的声明

允许声明：predictor 定向合同在锁定 Scala 门禁中通过；发布的 Spinal `core_top` 生成、端口合同和 Yosys 静态检查通过；mixed `func_lab19` 功能路径到 syscall 且无 DiffTest mismatch。

禁止声明：官方 smoke gate PASS、predictor 与 a158 完整等价、func-58/81 或 random 已通过、Vivado 已通过、CPU 已完全重构或已达到参赛 release 状态。

## 残余风险与下一候选

- 活动 fetch 接线属于流水控制影响，缺少 func-full 与 random 证据，状态不得超过 `implementation_in_review`。
- mixed overlay 是 `candidate_locked=false`、`baseline_exact=false`、`gate_eligible=false`，且仍混有旧 Verilog 依赖，只能作为诊断路径证据。
- 49-port contract 只证明名称、方向和宽度；不证明 AXI 握手、CDC、时序或 Fmax。
- strict lint 和 smoke warning policy 仍是 blocking issue。
- 下一候选是 LACC 独立 FSM 与 LACC-on 活动 top 集成；同时补齐官方 func/random/perf/system/fpga wrapper。
