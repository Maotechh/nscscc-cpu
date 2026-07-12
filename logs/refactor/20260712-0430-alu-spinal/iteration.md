# 20260712-0430-alu-spinal

- 状态：`draft`
- 分支：`refactor/20260712-0430-alu-spinal`
- Base / 初始 HEAD：`0d135ceed3ae9454b9cd2bca9f87a329c692d8c2`
- Owner / Agent：Codex
- 目标边界：`alu`

## 选择理由

ALU 是 `a158aa8` 活动路径中 blast radius 最小、依赖最少且 golden oracle 最强的组合叶子。历史模块只有 78 个输入位和一个 32-bit 输出，可以用 Yosys 对全部输入做组合形式等价；现有 Scala 明确只是错误的 4-bit local smoke 合同，尚不能替换活动 RTL。component replacement harness 已在 prerequisite `0d135ce` 推送，因此本轮可以完成第一个真实 Spinal 组件替换，而不扩散到性能优化。

## 初始事实

- 开始前 branch/HEAD：`refactor/20260711-1533-component-overlay@0d135ce`，工作树干净；远端同分支也是 `0d135ce`。
- `origin/main` 保持 `20cae5fd66391f4a1bccc1b87035be421039144b`。
- remote：`origin=https://github.com/Maotechh/nscscc-cpu.git`。
- 从已推送 prerequisite 创建 stacked branch；没有新建项目目录，没有 PR，不自动 merge。
- Golden `alu.v` 是 14-bit masked-OR 合同并包含 ANDN/ORN；现有 Scala `ALU` 是 4-bit priority mux，额外暴露 overflow/cmp，测试明确否认 golden equivalence。
- 现有 Makefile 缺 `elaborate/generate/port-check/lint/yosys-check/unit/formal` 入口；本轮需在实现前补齐 fail-closed harness。

## 行为合同

见 `docs/contracts/alu.md`。公开合同固定四个端口、14-bit bitmask、zero/multi-hot masked-OR、无时钟/复位和无状态。

## 尝试与失败

- 第一次 `make scala-check` 因测试 `doSim` seed 使用 `Long` 而 Spinal API 要求 `Int` 失败；修正为固定 `Int` seed，并用带 heartbeat 的测试壳隔离纯组合 DUT 后，Scala 4/4 通过。
- 第一次 `make generate TARGET=alu` 返回非零：SBT Unix socket 路径超过系统长度限制。将 runtime/home/tmp/global 迁移到短 `/tmp/nag-<hash>` 目录后，生成器两次运行均通过并清理 runtime。
- 第一次 `port-check` 暴露 Yosys JSON backend 不能直接处理未 lowered process；增加 `proc` 后端口检查通过。该失败保留为 harness 设计证据。
- Scala gate 初版只要求一个 `verilatorScript.sh`，会漏审多测试仿真。将策略改为所有 script 均必须满足锁定 warning policy；3 个 script（legacy、directed、random）均通过。

## 当前门禁

dirty source dev gate 结果：Scala 4/4、elaborate 1/1、generate 2/2、port-check 1/1、Verilator lint 1/1、Yosys check 1/1、Yosys formal 1/1、ALU unit 3/3（directed + 4096 fixed-seed random + generated-port test）。这些结果待 source commit 后重跑并绑定 clean HEAD。

当前 Vivado 2023.2 只用于 doctor；本组合叶子迭代不做 FPGA 提交或性能优化。whole-CPU diagnostic 尚未运行。

## 功能、性能与资源

- 功能：待模块差分；whole-CPU baseline 仍有已知 `func_lab19` mismatch。
- 模块差分：生成 RTL SHA256 `317d142c64edd5a5e6984a90565184c26b90c1c43f7fd0fd83a14b39f753a6c8`；与 golden `5d73aa7f57367311f5d6f6fad5f750e5f97bc2bd1e52c7d0b9e543596ffc7d32` 的 Yosys `equiv_status -assert` 已通过，覆盖 78 个输入位。
- 性能：不优化，只禁止无证据的功能/时序回退 claim。
- 资源/Fmax：本轮 change-impact matrix 不要求 Vivado；未执行前不声明数字。

## 回退

revert 本迭代提交即可恢复 prerequisite。旧 `a158aa8` ALU 继续作为 oracle 和参赛稳定路径，直到 replacement 达到规定门禁。

## PR 状态

`awaiting_implementation`；未来只能创建 stacked Draft PR，不自动创建、ready 或 merge。

## 下一候选

完成 ALU 后根据可执行 oracle 与依赖重新选择，不预先承诺固定模块顺序。
