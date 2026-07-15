# 20260715-1300-typed-axi-boundary

## 本轮补充证据

- 修改前后 generated `core_top` 已从 `b8962b6` 与 `c81af38` 的提交 blob 独立导出；Yosys 0.33 flattened `equiv_simple + equiv_induct + equiv_status -assert` 返回 0，18150 个 `$equiv` cell 全部 proven、0 个 unproven。机器证据：`evidence/sequential-equivalence.json`。
- pure-Spinal diagnostic `func_lab19` 完成 174059 条指令和 609660 个周期，以 syscall 结束，`first_mismatch=null`；严格 warning policy 和 diagnostic gate eligibility 仍失败，不能写成正式 smoke PASS。
- 自动化 wrapper 虽返回 0，但 381 项中 10 项 skip；总 automation gate 按零 skip 合同为 FAIL。
- 独立只读审查接受上述窄 claim，拒绝 release-ready/完整功能集 claim，见 `reviews/independent-review.md` 与 `reviews/independent-summary.json`。

- 状态：`draft`
- 分支 / Base SHA / Head SHA：`refactor/20260714-1650-consolidated-spinal` / `b8962b6c194c11d01747adb2a7269216df01dce3` / `c81af389d67063d99beb2caf46260df07a0a5a70`
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
- `chiplab-doctor`：锁定 chiplab commit/gitlink、symlink、工具版本和哈希全部 PASS；证据 `evidence/chiplab-doctor.json`。使用 `/opt/chiplab-reference` Linux ext2/ext3 副本；Windows 挂载副本的 v9fs/symlink 失败不作为正式环境。
- `core_top`：2/2 可复现生成 PASS，fresh generator RTL SHA256 `fc8ebacfd8fd858899e210380c30a5d5e2e883b31b36841a72a91e1fcc4d04c0`；证据 `evidence/generate.json`。
- package / publish：49 端口、17 input、32 output、`TLBNUM=32`、单一 top；tracked package 与 fresh package 逐字节一致，SHA256 `51e400e3d3c56bed3201c9599224aaaf361c22d8f1dc272054094adc8a9e9ebc`；证据 `evidence/contract.json`、`evidence/package.json`、`evidence/publish-check.json`。
- candidate closure：旧 CPU module 定义/实例均为 0，未解析实例为空；PASS，证据 `evidence/candidate-closure.json`。
- typed AXI boundary：Backend typed contract、CoreTop raw pin owner、25 个输出和 11 个输入逐字段 direct mapping 全部 PASS；证据 `evidence/typed-axi-boundary.json`。
- replacement reachability：active runtime replacement SHA 与 tracked package 一致，PASS；证据 `evidence/replacement-reachability.json`。
- overlay 修复：mixed/pure profile 均保留 `LICENSE` 和 upstream `mycpu.h`；pure overlay 只保留 `mycpu_top.v` 加支持文件，证据 `evidence/chiplab-overlay.json`、`evidence/chiplab-overlay-manifest.json`。mixed overlay compile 仍因旧 `div.v` 的 Verilator `div` 命名冲突失败，证据 `evidence/rtl-smoke-mixed.json`。
- pure `func_lab19`：configure、编译、仿真完成；174059 instructions、609660 clocks、DiffTest loaded、`end_by_syscall=true`、test end reached、`first_mismatch=null`。整体 smoke 因 DUT 40/官方 365 warnings 失败，且 diagnostic profile 不具 gate eligibility；证据 `evidence/rtl-smoke.json`。这只支持功能观察 claim，不支持正式 smoke gate 或 release ready。
- Yosys：hierarchy/check PASS，0 warning；证据 `evidence/yosys-check.json`。
- Verilator lint：严格零告警门禁 FAIL，共 73 条 `DECLFILENAME/UNUSEDPARAM/UNUSEDSIGNAL`；没有 WIDTH、LATCH、UNDRIVEN、UNOPTFLAT 或组合环类错误。未添加 waiver，证据 `evidence/lint.json`。
- 自动化：Windows 原生 wrapper exit 0，但 `381 tests / skipped=10`；其中 371 个实际执行通过、10 个可选依赖缺失而 skip。WSL 首次因显式 `GIT_DIR/GIT_WORK_TREE` 污染测试临时仓库而 4 项失败；按零 skip 合同总门禁标 FAIL，不能宣称自动化全通过。

## 失败尝试

- Windows 首次 `scala-check` 把 `/opt/chiplab-tools/root` 解释为 `D:/opt/...`，工具链检查失败。
- WSL 首次因 worktree `.git` 内是 Windows 绝对路径，无法解析 HEAD；之后只对当前 repo 显式设置 Git 元数据路径。
- 第一次 Scala 编译缺少 `spinal.lib._`；第二次发现 AXI address 的 `UInt/Bits` 不匹配；均按明确编译错误修复。
- 首次 publish-check 正确发现 tracked package 仍是旧 SHA `ded57a...cad`；发布 fresh package 后通过。
- 2026-07-15 远端 fetch 因 GitHub 443 不可达失败；失败前本地 tracking ref 显示 HEAD 与 origin 仍为 `b8962b6`，不能把这次 fetch 声称为远端最新确认。
- Claude review MCP 已实际调用，但缺少 `GEEKPIE_CLAUDE_API_KEY`，状态为 `unavailable`；原始错误见 `reviews/claude-raw.md`，不得表述成 Claude 已审核。
- overlay 首次使用错误 Git 环境导致 doctor 误读 CPU SHA；后续改用 `/tmp/nscscc-typed-src` clean clone，doctor 正确 PASS。mixed overlay 首次误删 `mycpu.h`，修复提交为 `c81af389d67063d99beb2caf46260df07a0a5a70`。

## 风险、回退与下一步

- 当前证据支持“Backend 已使用 typed AXI3 contract、外部 49 pin 合同保持、修改前后 generated RTL 在记录的 Yosys 流程下顺序等价，以及 pure diagnostic `func_lab19` 未观察到 mismatch”。不得外推为正式功能集或 release gate PASS。
- 未通过或未运行：严格 lint、正式 gate-eligible locked smoke、58/81 功能集、random DiffTest、perf20、U-Boot/Linux、Vivado implementation/timing/bitstream、`a158aa8` golden 与当前整机的完整顺序等价。
- 回退：revert 本迭代提交即可恢复旧 Backend raw pin 接口与旧发布 RTL；不修改 `main`、官方 chiplab reference 或稳定分支。
- 下一步：修复 mixed overlay 的旧 Verilog 输入/strict warning 后再申请正式 smoke；PR 保持 draft，不自动合并。
