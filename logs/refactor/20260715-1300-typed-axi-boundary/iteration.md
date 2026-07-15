# 20260715-1300-typed-axi-boundary

- 状态：`draft`
- 分支 / Base SHA / Head SHA：`refactor/20260714-1650-consolidated-spinal` / `b8962b6c194c11d01747adb2a7269216df01dce3` / 提交后回填
- Owner / Agent：Codex `/root`
- 选择边界：让 `CoreTopCompat` 成为唯一接触 chiplab AXI3/WID 原始 pin 的层；`SpinalCoreBackend` 只暴露 typed `Axi3Compat`。该边界直接修正第五部分已审计出的遗留端口所有权问题，同时不改 cache/AXI bridge 状态机。
- Golden / 固定工具：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`；JDK `17.0.19+10`、SBT `1.10.11`、Scala `2.13.16`、SpinalHDL `1.14.2`、Verilator `5.020`、Yosys `0.33`。

## 行为合同与修改

- AR/AW/W 为 master，R/B 为 slave；保留 AXI3 `WID`、8-bit `ARLEN/AWLEN`、全部 payload 位宽和 ready/valid 方向。
- `Axi3ReadAddress.address` 与 `Axi3WriteAddress.address` 使用 `Bits(32 bits)`，与活动 bridge 的原始位向量类型一致。
- `CoreTopCompat` 保留 49 个官方 raw pin，并逐字段适配 `Axi3Compat`；Backend 不再重复声明 raw AXI pin。`OpenLa500AxiBridge` 内部仍是待后续迁移的 raw leaf，本轮不声称其已采用 typed memory/AXI contract。
- 未修改 AXI 仲裁、cache、uncached、backpressure、reset、debug、CommitEvent 或流水策略。
- 修改文件：`Axi3Compat.scala`、`CoreTopCompat.scala`、`SpinalCoreBackend.scala`、生成发布 RTL 与 replacement hash、本迭代日志。

## 门禁与证据

- `scala-check`：wrapper exit 0，4/4 PASS，31 个 ScalaTest 全通过，固定依赖 cache 和隔离源码稳定；证据 `evidence/scala-check.json`。
- `core_top`：2/2 可复现生成 PASS，fresh generator RTL SHA256 `fc8ebacfd8fd858899e210380c30a5d5e2e883b31b36841a72a91e1fcc4d04c0`；证据 `evidence/generate.json`。
- package / publish：49 端口、17 input、32 output、`TLBNUM=32`、单一 top；tracked package 与 fresh package 逐字节一致，SHA256 `51e400e3d3c56bed3201c9599224aaaf361c22d8f1dc272054094adc8a9e9ebc`；证据 `evidence/contract.json`、`evidence/package.json`、`evidence/publish-check.json`。
- candidate closure：旧 CPU module 定义/实例均为 0，未解析实例为空；PASS，证据 `evidence/candidate-closure.json`。
- typed AXI boundary：Backend typed contract、CoreTop raw pin owner、25 个输出和 11 个输入逐字段 direct mapping 全部 PASS；证据 `evidence/typed-axi-boundary.json`。
- replacement reachability：active runtime replacement SHA 与 tracked package 一致，PASS；证据 `evidence/replacement-reachability.json`。
- Yosys：hierarchy/check PASS，0 warning；证据 `evidence/yosys-check.json`。
- Verilator lint：严格零告警门禁 FAIL，共 73 条 `DECLFILENAME/UNUSEDPARAM/UNUSEDSIGNAL`；没有 WIDTH、LATCH、UNDRIVEN、UNOPTFLAT 或组合环类错误。未添加 waiver，证据 `evidence/lint.json`。
- 自动化：Windows 原生环境 `381 tests / OK / skipped=10`；其中 371 个实际执行通过、10 个可选依赖缺失而 skip。WSL 首次因显式 `GIT_DIR/GIT_WORK_TREE` 污染测试临时仓库而 4 项失败；因此自动化测试集仍标 `warning`，不能宣称 skipped=0。

## 失败尝试

- Windows 首次 `scala-check` 把 `/opt/chiplab-tools/root` 解释为 `D:/opt/...`，工具链检查失败。
- WSL 首次因 worktree `.git` 内是 Windows 绝对路径，无法解析 HEAD；之后只对当前 repo 显式设置 Git 元数据路径。
- 第一次 Scala 编译缺少 `spinal.lib._`；第二次发现 AXI address 的 `UInt/Bits` 不匹配；均按明确编译错误修复。
- 首次 publish-check 正确发现 tracked package 仍是旧 SHA `ded57a...cad`；发布 fresh package 后通过。
- 2026-07-15 远端 fetch 因 GitHub 443 不可达失败；失败前本地 tracking ref 显示 HEAD 与 origin 仍为 `b8962b6`，不能把这次 fetch 声称为远端最新确认。
- Claude review MCP 已实际调用，但缺少 `GEEKPIE_CLAUDE_API_KEY`，状态为 `unavailable`；原始错误见 `reviews/claude-raw.md`，不得表述成 Claude 已审核。

## 风险、回退与下一步

- 当前证据只支持“Backend 已使用 typed AXI3 contract，外部 49 pin 合同与生成层级保持一致”。完整行为不变仍需官方 smoke/更完整回归支撑。
- 未通过或未运行：严格 lint、58/81 功能集、random DiffTest、perf20、U-Boot/Linux、Vivado implementation/timing/bitstream、完整顺序形式等价。
- 回退：revert 本迭代提交即可恢复旧 Backend raw pin 接口与旧发布 RTL；不修改 `main`、官方 chiplab reference 或稳定分支。
- 下一步：从本次提交创建 pure-Spinal overlay，运行锁定 chiplab `func_lab19`；完成独立审查与 Claude bridge 尝试后再更新本日志。PR 保持 draft，不自动合并。
