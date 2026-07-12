# 20260712-0430-alu-spinal

- 状态：`draft / implementation_in_review`
- 分支：`refactor/20260712-0430-alu-spinal`
- Base SHA：`0d135ceed3ae9454b9cd2bca9f87a329c692d8c2`
- 实现与验证目标 SHA：`ecdc699e10a20c4071f80de55e39f8a4255aa985`（RTL/tool gate 结果在其父提交 `4743235`，合同仅作语义澄清）
- Owner / Agent：Codex
- 目标边界：`alu`

## 选择理由

ALU 是 `a158aa8` 活动路径中依赖最少、blast radius 最小且 golden oracle 最强的组合叶子。它只有 78 个输入位和一个 32-bit 输出，可用 Yosys 对全部输入变量做组合形式等价；前置 component overlay 已能把提交过的 replacement blob 注入锁定 chiplab。本轮只迁移 ALU，不修改 decode、流水、cache、CSR、mul/div，也不做性能优化。

## 初始事实

- 从已推送 prerequisite `refactor/20260711-1533-component-overlay@0d135ce` 创建 stacked 分支；未修改或合并 `main`。
- `origin/main` 在迭代开始时为 `20cae5fd66391f4a1bccc1b87035be421039144b`。
- Golden 为 `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/alu.v`，SHA256 `5d73aa7f57367311f5d6f6fad5f750e5f97bc2bd1e52c7d0b9e543596ffc7d32`。
- 历史 Scala `ALU` 是不兼容的 4-bit local smoke 合同；本轮没有把它或 `CPUCoreFlat` 当作 golden。

## 行为合同

合同见 `docs/contracts/alu.md`：

- 端口固定为 `alu_op[13:0]`、`alu_src1[31:0]`、`alu_src2[31:0]` 和 `alu_result[31:0]`。
- 14-bit operation 是 bit mask；zero-hot 输出 0，multi-hot 将各选择结果按位 OR。
- 保留 ANDN、ORN、共享加法器和共享右移器的历史语义。
- 模块无时钟、无复位、无状态，生成名固定为 `alu`，公开端口无 `io_` 或 `_zz_`。

## 实现

- 新增 `openla500.execute.OpenLa500Alu` 和 fail-closed 独立生成器。
- 新增 directed、边界、zero/multi-hot 和固定 seed `0x158aa8` 的 4096 组随机测试。
- 新增 `make elaborate/generate/port-check/lint/yosys-check/unit/formal TARGET=alu`。
- 提交生成 RTL 与 replacement spec；最终 RTL SHA256 为 `1349173904c772225ed4184a7e65aa88f7278fbcd060d33d81c966954c128146`，大小 6398 字节。
- 首轮生成 RTL 含 Spinal 默认 `timescale`，在 whole-CPU 编译中新增 10 条 `TIMESCALEMOD` warning。已设置 `withTimescale=false` 并添加回归断言，未用 waiver 掩盖。

## 尝试与失败

1. 第一版 Scala 仿真 seed 使用 `Long`，而 Spinal API 要求 `Int`；修正为固定 `Int` seed 后通过。
2. 第一版 generation 因 SBT Unix socket 路径过长失败；生成 gate 改用短临时 runtime workspace，并验证清理。
3. 第一版 port-check 未先执行 Yosys `proc`；补齐 lower process 后端口检查通过。
4. 第一版 replacement SHA256 `317d142c...` 带 `timescale`。旧 mixed smoke 为 652 warnings，只作为失败历史；最终证据全部在新 HEAD 和新 overlay 上重跑。
5. Claude review job `a016bb2337534c96b27ea3bd984076ed` 在模型启动前因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败。没有 Claude response，不能把降级复审称为 Claude 审核。

## 最终门禁

- Windows doctor：PASS；锁定 Vivado ML Standard 2023.2 launcher/binary/hash/version 均匹配。
- chiplab doctor：PASS；chiplab `a2e11b3`、myCPU gitlink `aa3bde1`、JDK 17.0.19、Verilator 5.020、Yosys 0.33、SBT 1.10.11 和 LA32R 工具链均匹配 lock。
- 自动化测试：WSL `Ran 137 tests ... OK`；负例故意打印错误但总进程为 0。
- Scala：format、compile、test-compile、test 共 4/4 PASS；依赖缓存未漂移。
- elaborate / generate：PASS；两次独立 generation 均字节一致，提交的 `alu.v` 与生成物完全相同。
- port-check：PASS；只有四个合同端口，无额外 clock/reset。
- Verilator `--lint-only -Wall`：PASS，0 warning。
- Yosys `hierarchy/proc/opt/check -assert`：PASS。
- unit-diff：3/3 PASS，4096 fixed-seed random，skipped=0。
- formal：`equiv_make/equiv_simple/equiv_status -assert` PASS；对 78 个输入变量证明 2-state 组合等价。该措辞不是声称枚举了 `2^78` 个向量。

## 官方 chiplab 诊断

全新 candidate 与 mixed overlay 均实际编译并运行官方发现的 `func/func_lab19`，没有复用旧 `8d2b85b` 结果：

| 项目 | candidate `a158aa8` | mixed `4743235` |
|---|---:|---:|
| executed / skipped | 1 / 0 | 1 / 0 |
| 功能结果 | FAIL | FAIL |
| instructions | 172552 | 172552 |
| cycles | 602903 | 602903 |
| 首个 mismatch PC | `0x1c07c79c` | `0x1c07c79c` |
| trace SHA256 | `8efa7942...acb` | `8efa7942...acb` |
| DUT / 总 warnings | 280 / 644 | 278 / 642 |

首错均为 `t0` expected `0x000006e2`、actual `0x00000008`。mixed 仅支持“该单一失败用例没有出现更早的可见回退，且最终 ALU 消除两条旧 warning”；它不支持 CPU 正确、integrated PASS 或官方功能通过。642 条未批准 warning 仍使 compile policy FAIL。

## 功能、性能与资源

- 模块功能：端口、directed/random 和 Yosys 组合形式等价均有机器证据。
- 整机功能：`func_lab19` 真实执行但失败；58/81、random DiffTest、perf、U-Boot、Linux 均未执行。
- 资源/Fmax/FPGA：本轮是组合叶子替换，change-impact matrix 不要求 FPGA job；仅用 Vivado 2023.2 doctor 核对安装。未执行前不声明任何资源或时序数字。

## Claim 与状态

- C1：支持窄范围模块 claim，即提交的 Spinal-generated ALU 在锁定工具下可复现、端口匹配，并通过 2-state 组合形式等价。
- C2：支持单一 `func_lab19` 诊断观察，即 candidate/mixed 首错和 trace 相同，mixed 少两条 DUT warning；两侧仍 FAIL。
- C3：不支持“ALU 已通过完整 CPU 官方功能验证”。
- Claude required review unavailable，因此 `docs/refactor/status.yml` 只提升到 `implementation_in_review`，不写 `differential_pass`。

## 回退

revert 本迭代提交即可恢复 prerequisite；历史 `a158aa8:rtl/alu.v` 继续保留为 oracle 和参赛稳定实现。禁止删除 golden 或改写主分支历史。

## PR 状态

`awaiting_push`。只生成 stacked Draft PR 草稿；按用户要求不自动创建 PR、不标记 ready、不合并。

## 下一候选

动态选择结果首选 `mul-golden-harness` prerequisite，随后才是独立 `mul-spinal` 替换。原因是活动 `mul.v` 边界窄且一拍时序合同可执行，但当前 Make/tool gate 仍硬编码 ALU，必须先建立 golden harness；不把 harness 与实现混在同一 PR。
