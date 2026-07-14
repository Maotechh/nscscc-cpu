# 20260714-0302-spinal-active-backend

- Status: `implementation_in_review`
- Branch / Base SHA / Head SHA: `refactor/20260714-0302-spinal-active-backend` / `78efdf97b6208da3806fcbc02dca69061284d3b7` / `pending`
- Owner / Agent: Codex `/root`
- Selected boundary and selection reason: 活动整机 backend。该边界把已经迁移的 IF/ID/EX/MEM/WB、CSR、TLB、Cache、AXI 和 mul/div 连接为官方 `core_top`，并直接解除活动顶层对 legacy CPU Verilog BlackBox 的依赖。
- Golden reference and locked tool versions: `a158aa8:rtl/`；工具版本见 `reference/manifest.lock`；Vivado 固定为 2023.2。

## 行为合同

- 生成定义名保持 `core_top`，49 个官方端口和 `TLBNUM=32` 不变。
- `aclk/aresetn` 构成显式同步复位 ClockDomain，活动 backend 不得实例化 `openla500_legacy_core`。
- EX/MEM 的级占用状态与 GPR forwarding enable 是不同合同。Decode 只能在 producer 的 `writeEnabled` 为真时旁路数据。
- `CommitEvent` 延迟一拍，GPR/CSR `ArchState` 保持实时，以匹配 golden 的 NBA/DPI 观察顺序。
- `DIFFTEST_EN` 下实例化官方七个 DPI 模块；综合配置不保留未解析 DPI 依赖。

## 本轮实现

- 接入完整纯 Spinal `SpinalCoreBackend`、官方 `CoreTopCompat` 和 DiffTest adapter。
- 将 `DecodeForward.valid` 重命名为语义明确的 `writeEnabled`，backend 分别连接 `execute.io.forward.writeEnabled` 和 `memory.io.forward.writeEnabled`。
- Legacy adapter 继续从 golden forwarding bus bit 37 读取写使能，保持旧模块合同。
- 新增 `DecodeForwardingSpec`：验证被占用的 store 不得把有效地址伪装成 GPR 写旁路，同时验证真实 GPR 写仍会旁路。
- 新增 `test_forwarding_integration_contract.py`：直接检查生成 RTL 中 EX/MEM 的 `writeEnabled` 进入 Decode，而 stage-valid 只进入 `executeOccupied/memoryOccupied`。
- 更新完整生成 RTL和三份 replacement manifest；新 package SHA256 为 `2646383fc6e201c0108c018c780fb4240301beb53e8dfc6eacf00149ab5586cc`。

## 尝试、失败与诊断

- Windows Scala gate 因锁定工具位于 `/opt` 不可用；WSL 直接读取 Windows worktree 又因 `.git` 内是 Windows 路径失败，因此继续使用现有 WSL 原生验证 clone。
- `210f596` 的官方 smoke 构建成功但 600.054 秒超时，parser 观察到 0 条提交；FST 证明 IF/AXI/WB 活动，随后定位为缺少官方 DiffTest DPI 实例。
- `39501d1` 加入 adapter 后，官方 smoke 在 6.126 秒内自然结束，NEMU 实际推进 162,373 条提交、569,009 clocks；首错为 PC `0x1c0752b8` 的 store 地址。
- 相邻指令 `29801273` 和 `2980127b` 均以 r19 为基址、立即数为 4。Golden trace 两条有效地址均为 `0x1d0004`，candidate 第二条为 `0x1d0008`。
- 根因不是 DPI 调度或第一条 store event 丢失，而是 backend 把 EX/MEM 的 stage-valid 接到了 Decode forwarding enable。前一条 store 的 destination 字段恰为 r19，导致其 ALU 地址 `0x1d0004` 被错误旁路为 r19，再加立即数 4。
- 新测试首次运行时功能断言通过，但 gate 因 93 个测试顶层裁剪 warning 失败；补 `keepAlive` 后 warning 消失。第二次仍因测试 Verilator 未显式重新启用四项 locked warning 而被策略拒绝；补齐 `-Wwarn-*` 后严格 gate 通过。
- 更新 Scala 后首次 `generate` 的 publish-check 按设计拒绝旧 tracked package；替换生成 RTL并同步 manifest hash 后通过。

## 门禁结果

- Scala: 4/4 PASS，25 tests PASS，0 skip。证据：`evidence/scala-forwarding-fix.json`。
- 双次生成: 2/2 PASS，可复现；wrapper SHA256 `97486e9577f2cebbc5d1b604fddee75f131e80bc8602e6951fee1efd2de7cbf8`。
- Package/publish: PASS；package SHA256 `2646383fc6e201c0108c018c780fb4240301beb53e8dfc6eacf00149ab5586cc`。
- 官方端口: 49/49 PASS；Yosys hierarchy/proc/check PASS，无 warning。
- 严格 Verilator lint: FAIL，86 条未批准 warning；不标记 PASS。
- Python 自动化: 327 PASS，0 FAIL，10 个平台互斥测试 skip；该项保持 warning，不用 skip 冒充全通过。证据：`evidence/automation-forwarding-fix.json`。
- Vivado ML Standard 2023.2 build 4029153 doctor: PASS；本次尚未重跑 implementation/bitstream。
- 官方 smoke: `39501d1` FAIL，但已经从 0 提交超时推进到 162,373 条真实 DiffTest 提交。forwarding 修复需在干净提交的新 overlay 中复测。

## 功能、性能与资源变化

- 定向行为已证明连续 store 不会因非写指令产生伪 forwarding；整机 smoke 尚未对本修复复测，因此只声明 unit contract 通过。
- 未运行性能、资源、timing 或 bitstream，不作相关声明。

## 残余风险

- forwarding 修复后的官方 smoke 尚未运行；后续 mismatch 未知。
- 严格 lint 仍有 86 条未批准 warning。
- Golden 可观察的 BTB/RAS 行为、LACC、完整随机 DiffTest、perf、Linux 和 FPGA release gate 尚未完成。
- 锁定 baseline 自身最终在 `0x1c07c79c` 失败；candidate 达到该点后仍需区分 baseline 缺陷与重构回归。
- Claude bridge 缺少可用后端/API key；本次按契约降级为独立子代理只读审查，不能表述为 Claude 审核。

## 回退与下一步

- 回退方式：revert 本迭代提交；不修改或合并 `main`。
- PR 状态：`awaiting_next_push` / draft；代理不自动创建、标记 ready 或合并 PR。
- 下一步：提交并推送本修复，从提交 SHA 创建全新 locked overlay，复跑官方 `func/func_lab19`；只根据新的首个真实 mismatch 继续修复。
