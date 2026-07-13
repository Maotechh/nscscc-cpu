# 20260713-2245-core-top-contract

- 状态：`audit_pass / draft / awaiting_push`
- 分支 / Base SHA / 实现 SHA：`refactor/20260713-2245-core-top-contract` / `b2946f8ac93fc9ccfa9c8748bb53f444976c36cb` / `72dc250fa7fd10e7535b1ef52912b10562c6d159`
- Owner / Agent：Codex
- 边界：锁定 `core_top` 外部合同与现有 compatibility harness 的只读复核

## 选择理由

活动流水模块继续迁移前，需要确认所有 leaf adapter 最终面对的官方顶层边界没有漂移。本迭代不重复实现已有 `CoreTopCompat`，只验证锁定 chiplab、team golden、Spinal 生成入口和 fail-closed port gate 是否一致；不修改流水、legacy backend 或 active overlay。

## Golden 与行为合同

- Team golden：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/mycpu_top.v`。
- Locked chiplab myCPU：`aa3bde1f3e720e71c2c78d6b81930d797b810149:mycpu_top.v`。
- 两者规范化 `core_top` 表头 SHA256 均为 `43c1c564fe0288dca984a01fd8cffc6d385c4d5c7c0839fab3dd41103b4fc309`。
- 合同固定 `TLBNUM=32`、49 个端口（17 input、32 output）、`aclk` 上升沿和外部低有效 `aresetn`。
- AXI 保留 AXI3/WID 风格；`arlen/awlen` 为 8 bit。debug 保留 `break_point/infor_flag/reg_num/ws_valid/rf_rdata/debug0_wb_*`。

## 审计结论

1. 当前项目已经采用 `CoreTopCompat`，生成定义名为 `core_top`；当前活动生成入口不应使用简化的 `CPUCoreFlat`。
2. 双次 Spinal 生成字节一致，wrapper SHA256 为 `2bf5d47273ffd49e37580da5d7c04dcb0b24987461dd94663afcf14c43604704`。
3. 打包结果 SHA256 为 `fec641117e538dfb79eedb0e4afffeb3690594e84ffb9799c5409d8f690258a3`，与 tracked replacement/spec 一致。
4. Yosys 结构检查确认 49/49 同名连接、唯一 `openla500_legacy_core` backend，以及 top/backend 的 `TLBNUM=32`。
5. wrapper-only Verilator lint 和 Yosys check 通过，均明确标记 `full_package_static_validated=false`。
6. 独立审核发现 `clock_reset` metadata 仅检查字段存在、未检查内容。现已加入精确 schema/value 比较和 edge、reset active level、wrapper latency mutation 负控；修复后 gate 会拒绝该 metadata 漂移。

## 文件变更

- `tools/core_top_gate.py`：锁定 `clock_reset` 的字段和值。
- `tests/test_core_top_gate.py`：新增三类 metadata mutation 负控。
- `logs/refactor/20260713-2245-core-top-contract/`：中文过程、机器可读结果和审核记录。

## 尝试与失败

- 直接在 Windows worktree 下从 WSL 运行 `chiplab-doctor` 失败：WSL Git 无法解析 `.git` 中的 Windows 路径。这是执行环境路径问题，不是 chiplab 内容失败。
- 随后在 `/tmp` 建立同一 SHA 的 Linux clone，保持源码 worktree 不变；锁定 chiplab commit、myCPU gitlink、symlink、工具版本和哈希全部通过。
- Claude review job `c69a87a68a234c398fc9ac264f4adfed` 在模型启动前因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败，不能声称 Claude 审核通过。

## 命令与门禁

- Windows doctor：PASS，包含 Vivado ML Standard 2023.2 build 4029153 和可执行文件哈希。
- Linux chiplab-doctor：PASS。
- commit-bound Scala gate：scalafmt、compile、test compile、tests 4/4 PASS。
- `make core-top-contract`：PASS，两个锁定源的 49 端口合同一致。
- `make TARGET=core_top generate`：2/2 PASS，0 skip，可复现。
- package / publish-check / port-check / lint / yosys-check：修复后 fresh OUT_DIR 全部 PASS，evaluator SHA256 为 `4424290fdb8d6da65764b7f701bf19cbd71c44b9d4d214f6dc3843c3f3d9a3fb`。
- `python -m unittest tests.test_core_top_gate tests.test_iteration_validation`：37/37 PASS。
- 全量 Python discovery：329 项、319 PASS、0 FAIL、10 个既有 platform/optional SKIP；仅记为 warning，不冒充无 skip 的 required gate。
- `python -m py_compile tools/core_top_gate.py tests/test_core_top_gate.py`：PASS。
- `git diff --check`：PASS。
- 官方 func smoke 未运行；本迭代不改变 RTL 行为且不修改 active overlay，保持 draft 并记为 unavailable，不能从结构 gate 推导功能结果。

## 功能、性能与资源影响

本迭代只修改 Python 合同校验和负控，没有修改 RTL 或 Scala 实现；功能、周期、Fmax 和资源 delta 均为“不适用”。未执行官方 func、random、perf、Linux 或 Vivado implementation/bitstream，不能推导这些 gate 的结果。

## 残余风险与回退

- 当前 wrapper 仍通过 BlackBox 依赖原 legacy Verilog CPU，不满足 Scala 唯一手写真源。
- clock/reset 证据只支持外部端口和显式 ClockDomain 声明；wrapper 无状态，不能证明未来 Spinal state 与 legacy 一拍 reset 注册行为等价。
- AXI/debug 证据只支持连接和接口形状，不支持协议事务、提交语义或整机功能正确。
- 回退方式：revert 本日志 PR；不影响现有 RTL、生成器或 overlay。

## PR 状态

只推送分支并保留 draft 草稿；不自动创建 PR，不 merge。

## 下一候选

在活动 integration 分支将已通过 leaf differential 的 IF/ID/EX/MEM/WB adapter 逐个接入锁定 `CoreTopCompat` backend 边界，并按实际改动重新运行官方 overlay/smoke；本日志不能替代该集成证据。
