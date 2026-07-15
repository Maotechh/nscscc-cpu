# 20260714-1534-btb-branch-replay

- Status: `blocked`；仅允许 Draft PR
- Branch / Base SHA / tested implementation SHA: `refactor/20260714-1534-btb-branch-replay` / `372eccc9b54fb5a80f08bc5af6dcc8944ea3e8fa` / `75523504912c1b390dc1d1e3cddb5c3a0cc43a27`
- Owner / Agent: Codex；两名独立只读子代理分别审核 BTB 时序和最终 claim
- Selected boundary and selection reason: `predictor/branch_replay`。上一迭代 mixed diagnostic 的首错是 `0x1c07cfdc` 分支重复提交；该边界直接阻塞整机 smoke，修改范围集中在 fetch/BTB 请求合同。
- Golden reference and locked tools: d22/a158 `rtl/btb.v` 的 `fetch_en_r/fetch_pc_r` 及无效返回清零语义；chiplab `a2e11b3`；Scala 2.13.16；SpinalHDL 1.14.2；Verilator 5.020；JDK 17.0.19；Vivado 2023.2。
- Behavior contract: `docs/contracts/btb-branch-replay.md`
- Rollback: revert 本迭代三个实现/发布 commit；保留 CACOP 分支为基线；不修改或合并 `main`。
- PR: `awaiting_pr`；不得自动创建、标记 ready 或合并。

## 修改

- BTB lookup valid 只对应上一拍真正接受的 fetch 请求，PC 也只在 `fetchEnable` 时更新。
- 无效或未命中时，返回 target/index 清零，避免 IF 的 golden 风格 lock/current 位或合并污染目标地址。
- 重新发布完整 Spinal `mycpu_top.v`，发布 SHA 为 `27b578ce4bf3c3157b65d2e05e2b45603da6e67e776a79a93630bede8981c6c0`，同步三个 replacement spec。
- 当前仍是 32-entry direct-mapped、always-taken 临时 predictor；64-entry、2-bit counter 和 RAS 未迁移。

## 尝试与失败

1. 第一次使用错误的 `active-reachable.json`，只替换 `mycpu_top.v`；旧 `div.v` 因 module/instance 同名编译失败，功能测试未运行。证据：`evidence/attempt-1-wrong-overlay-rtl-smoke.json`。
2. `9ff8f59` 改用正确的双 replacement overlay 后，单个 `func_lab19` 功能 parser 首次通过；随后独立审查发现 miss payload 未清零，不能以该中间提交收口。证据：`evidence/attempt-2-9ff-corrected-rtl-smoke.json`。
3. `7552350` 加入清零并重新发布后重跑所有本轮门禁。功能 parser 仍通过，但 strict lint 和 smoke warning policy 失败。
4. Claude bridge 已实际调用，因缺少 `GEEKPIE_CLAUDE_API_KEY` 在 reviewer 启动前失败；原始返回见 `reviews/claude-raw.md`，不得称为 Claude 审核。

## 最终门禁

- Scala：4/4 PASS；ScalaTest 25/25 PASS。
- generate：2/2 PASS 且可复现；package/publish PASS。
- port：49 个官方端口 PASS；Yosys hierarchy/check PASS。
- strict lint：FAIL；摘要不含可复核精确数量，因此不声明 standalone lint warning 数。
- chiplab doctor：PASS，锁定 commit、工具版本和哈希一致。
- overlay：`spinal-active-runtime.json`，两个 committed Git blob；`mixed_candidate`、`diagnostic`、`gate_eligible=false`。
- `func_lab19`：功能 parser PASS，174034 条指令、610132 拍、DiffTest enabled/loaded、无 mismatch、到达 `END by Syscall`。
- smoke 总 gate：FAIL，计数 1/1/0/1/0；DUT 258 条、官方环境 364 条未豁免编译 warning。
- 58/81、random、perf20、U-Boot、Linux、Vivado implementation/timing/bitstream、完整形式等价：未执行。

## Claim 与风险

允许声明：在锁定 chiplab 环境中，以两个提交 blob 构成的 mixed diagnostic overlay 运行单个 `func_lab19`，受测提交 `7552350` 的功能 parser 到达测试结束且没有观察到 DiffTest mismatch；旧 branch replay 症状在本次组合中未复现。总 smoke gate 因 warning policy 失败。

禁止声明：唯一根因已证明、official smoke gate PASS、完整 BTB、完整 CPU 等价、58/81、random、perf、Linux、Vivado 或完全重构通过。

残余风险：无 predictor 内部定向 harness；`good_trap=false` 且 parser 依赖 `END by Syscall`；DUT 为 mixed 而非 locked candidate；完整 predictor 和全回归仍缺失。

## 下一候选

- 建立 `hit -> addr_ok stall -> accept` 的 predictor/IF 定向 harness，覆盖无效 payload 和 lock 稳定性。
- 在独立迭代迁移并验证完整 64-entry/2-bit/RAS predictor；a158 的 64-entry 改动自身有 32/64 宽度不一致，不能未经验证直接当 truth。
- 解决 strict lint 后再扩展到完整功能和 random gate。
