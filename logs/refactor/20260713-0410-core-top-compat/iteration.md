# 20260713-0410-core-top-compat

- 状态：`draft / wrapped_golden / awaiting_push`
- 分支 / Base SHA：`refactor/20260713-0410-core-top-compat` / `7e5811f8faeca71a6f8fc3d7f9fd25aaac6587ab`
- 实现与复测 SHA：`0e2787fc5ab30e246da5be1c6080e2847b2645cf`
- Owner / Agent：Codex
- 目标边界：`CoreTopCompat` 官方顶层端口与显式 ClockDomain

## 选择理由

活动 ALU、mul、div 已有可审计 replacement；继续堆叶子不会解除整机集成阻塞。本轮转入官方 `core_top` 顶层合同，先从锁定 chiplab 与 `a158aa8` 提取真实端口，再实现只承载命名、方向、宽度、时钟/reset、AXI/debug 适配的 SpinalHDL 薄壳。

## Golden 与行为合同

- Team golden candidate：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/mycpu_top.v`。
- Locked chiplab myCPU：`aa3bde1f3e720e71c2c78d6b81930d797b810149:mycpu_top.v`。
- 两者主体不同，但规范化 module header SHA256 同为 `43c1c564fe0288dca984a01fd8cffc6d385c4d5c7c0839fab3dd41103b4fc309`。
- 合同固定 49 端口、17 input、32 output；`aclk` 上升沿，外部 `aresetn` 低有效；壳不新增状态、CDC、协议策略或周期。
- `TLBNUM` 默认 32并符号转发；本轮只验证 32。

## 实现与文件

- `CoreTopCompat`/generator：官方端口、显式 ClockDomain、临时 legacy BlackBox 后端。
- `core_top_gate.py`：锁定合同、机械 package、publish consistency、wrapper-only port/lint/Yosys。
- `spinal_generate.py`：锁定离线工具链、隔离 snapshot、两次字节一致生成、warning/SKIP fail-closed。
- `reference/component-replacements/core-top.json`：累计替换 `mycpu_top/alu/mul/div`。
- 合同和迁移决策：`docs/contracts/core-top-compat.md`、`docs/adr/0001-core-top-migration-backend.md`。

## 尝试与失败

- Windows worktree 的 `.git` 指针不能由 WSL Git 直接解析，最终门禁改在同一 base 的 `/tmp` 原生 Git 克隆执行，不修改仓库配置。
- 首次 Scala gate 仅 `scalafmtCheckAll` 失败；用锁定 scalafmt 格式化后 4/4 通过。
- 独立审查发现 OUT_DIR symlink/失败路径写入、isolated snapshot 未与源树比较、可省略 chiplab 合同、TLBNUM 注释误匹配及 tracked overlay 可能陈旧等 fail-open；均补负控和一致性 gate。
- 审查提出 `elaborate --runs 1` 时，Makefile 已在主线程改为 `--runs 2`；随后正式入口实际 2/2 通过。
- mixed overlay 首次从 detached `/tmp` clone 执行，被 branch provenance 检查拒绝；建立只用于验证的本地 `refactor/*` 分支后通过。
- identity compare 前两次因 locked/mixed 使用不同 OUT_DIR、doctor hash 不同而被拒绝；随后在同一 doctor/OUT_DIR 重跑。一次 locked compile freshness 失败，另建新 iteration 重跑后 artifact fresh。
- Vivado 首次 implementation 因 `dbg_hub` 临时目录 148 字符超过 146 限制失败；用 `subst R:` 缩短同一 staging 路径、重新运行同一 RTL/官方 Tcl 后完成。
- GitHub push 两次分别因 connect timeout 和 connection reset 失败；没有改写历史或转向 main。

## Pre-commit 门禁

- 自动化测试：296/296 PASS。
- Windows doctor：PASS，Vivado ML Standard 2023.2 build 4029153 与两个 executable SHA256 匹配 lock。
- Scala：4/4 PASS；elaborate 2/2；generate 2/2，0 warning、0 skip。
- wrapper RTL：8377 bytes，SHA256 `2bf5d47273ffd49e37580da5d7c04dcb0b24987461dd94663afcf14c43604704`。
- package/tracked/spec：54777 bytes，SHA256 `fec641117e538dfb79eedb0e4afffeb3690594e84ffb9799c5409d8f690258a3`，逐字节一致。
- wrapper-only port/lint/Yosys：PASS，49/49 同名连接、唯一 backend cell、0 warning/0 SKIP。

以上结果仍绑定 dirty-tree base，仅用于提交前检查。

## Commit-bound 门禁与结果

- clean `0e2787f`：doctor 2/2、自动化 296/296、Scala 4/4、elaborate 2/2、generate 2/2、publish consistency、49-port、wrapper-only lint/Yosys 全部 PASS。
- locked/mixed `func_lab19`：均 FAIL；首错 `0x1c07c79c`，172552 instructions、602903 clocks，trace SHA256 同为 `8efa7942...38acb`。
- 完整 Verilator warning：locked 644（DUT 280）、mixed 635（DUT 271），官方环境均 364；未批准 warning 使编译门禁失败。
- identity compare：parser/trace/ELF/ROM 相同，但 RTL projection、replacement bytes 和 warning counts 不同，状态 FAIL。
- Vivado 2023.2 官方 mixed overlay：synth/implementation/bitstream 完成；WNS `+0.364214 ns`、TNS `0`；LUT 19730、FF 19207、BRAM 12.5、DSP 8；bit SHA256 `f0c4729b...26666`。
- Vivado strict gate：post-route DRC 46 warning、batch log 155 warning line，无批准 waiver，因此 FAIL；未提交远程 FPGA job。
- Claude job `c819801d05724dd78cafa059dc58a4b7` 在模型启动前缺少 API key，状态 `unavailable`；两个本地独立审查和 artifact audit 不能冒充 Claude。
- evidence-check：21 个 tracked artifact、31 条命令记录、19 个 gate，schema/hash/review consistency PASS。

## 功能、性能与资源变化

- 只建立透明兼容边界；没有功能 PASS 增量，不能从相同失败 trace 推导等价或正确。
- 未运行 perf20，不能声明性能变化；wrapper 本身无状态和新周期。
- 仅取得 mixed 绝对资源数据，没有同一 Vivado run 的 locked 对照，不能声明资源 delta 或 Fmax 改善。

## 残余风险与回退

- 当前 package 仍包含机械改名的原 Verilog CPU，不能计入 Scala 唯一真源或流水/特权/存储迁移。
- wrapper-only 静态 PASS 不代表完整 legacy package 零 warning；完整 package 必须由锁定 chiplab 实际编译。
- 已知 `func_lab19` baseline 在 `0x1c07c79c` 失败；full/random 入口未实现；Vivado DRC warning 未批准；本 PR 必须保持 draft。
- 回退方式：revert 本迭代提交，恢复上一分支的 legacy `core_top` overlay；不得改写 main 历史。

## PR 状态

两次 push 因 GitHub 网络失败，当前 `awaiting_push`；未创建 PR、未标 ready、未合并。网络恢复后只推本分支并使用 `pr.md` 草稿，不自动创建 PR。

## 下一候选

建立统一 `CoreConfig`、directionless pipeline/memory/commit contracts，并据此并行迁移流水、特权、存储和 observe/predict 主干。
