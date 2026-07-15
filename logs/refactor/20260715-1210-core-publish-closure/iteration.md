# 20260715-1210-core-publish-closure

- 状态：`draft`
- 分支 / Base SHA / Head：`refactor/20260714-1650-consolidated-spinal` / `ba4ce0364a51e4c5ff9f5e674c20578c31e7e769` / `fe24e9a13fe8acbfc2e55117f4fdcc79c39b823c`
- 选择边界：发布一致性与 candidate hierarchy closure。审计确认生成层级已无旧 CPU Verilog 实例，但 tracked `mycpu_top.v` 曾落后于当前 32-entry predictor；同时 overlay 仍导出 16 个旧 Verilog 输入。该边界能直接阻止 stale RTL 和无依据的“纯 Spinal”声明。

## 实施与证据

- 生成 RTL 更新为当前 Scala/官方 32-entry predictor 对应 package，SHA256：`ded57a4a2b494e5342481a2d87e5b286ebb703bedde8e79df3fe299894dc4cad`。
- `scala-check`：scalafmt、compile、test-compile、test 全通过；证据 `evidence/scala-check.json`。
- `core_top` 2/2 可复现生成：通过；生成 module 共 20 个，包含 `core_top`、Spinal pipeline/cache/CSR/AXI/mul/div/predictor/perf 和 DiffTest adapter；证据 `evidence/generate.json`。
- package：49 个官方端口、单一 `core_top`、legacy backend absent；通过，证据 `evidence/package.json`。
- publish-check：fresh package 与 tracked replacement 逐字节一致；通过，证据 `evidence/publish-check.json`。
- candidate-closure：生成 RTL 恰好一个 `core_top`，旧 CPU 模块定义/实例均为 0，未解析实例为空（Difftest 前缀为允许的 simulator-owned 边界）；通过，证据 `evidence/candidate-closure.json`。
- 自动化新增 4 个 candidate-closure 单元测试，正/负 overlay 样例均通过。

## 失败尝试与边界

- 尝试删除 `SpinalCoreBackend` 的 `aclk/aresetn` IO，生成阶段出现真实 `PhaseCheckHierarchy` read-access violation；该未通过实验已回退，没有纳入 claim。
- pure overlay 文件集尚未启用：官方 wrapper 仍会把锁定的旧 Verilog 文件复制到临时 `IP/myCPU`，本迭代只提供检查工具，不删除官方输入。
- 未运行或未通过：官方 locked candidate smoke、58/81 功能集、random DiffTest、perf20、U-Boot/Linux、Vivado implementation/timing/bitstream、完整顺序形式等价。

## 审核、回退与下一步

- Claude MCP 调用因缺少 `GEEKPIE_CLAUDE_API_KEY` 不可用；raw 错误和 unavailable 状态已记录。PR 必须保持 draft。
- 回退：revert 本迭代提交可恢复旧 tracked package 和门禁入口，不修改 `main` 或官方 chiplab clone。
- 当前只支持“fresh package 与 Scala 源一致”和“生成层级无旧 CPU 模块实例”两个 claim；不支持“功能完整”“纯 overlay 已完成”或“release ready”。
- 下一候选：将 candidate-closure 接入隔离 chiplab overlay，先以 module-free/缺失旧文件的 profile 做 compile-only，再决定是否进入官方 smoke。
