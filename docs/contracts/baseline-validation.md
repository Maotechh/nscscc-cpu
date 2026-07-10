# Baseline validation 行为合同

## 目标

在锁定的官方 chiplab 中运行 `a158aa8` 活动 RTL，得到可重复、机器可读的最小功能证据。本边界不修改 CPU 功能语义，也不把候选 RTL 预设为正确 oracle。

## 输入

- `reference/manifest.lock` 锁定的 chiplab、myCPU gitlink、工具版本和二进制/依赖哈希。
- `reference/golden-rtl-files.lock` 列出的 22 个 `a158aa8` Git blob。
- `f89c604:mycpu.h` 支持头文件及官方 myCPU LICENSE。
- 官方 `configure.sh`、Makefile、testbench、NEMU 和 LA32R 软件镜像。

## 不变量

1. 只读 chiplab reference clone 不得修改；每次运行创建独立 Linux 文件系统副本。
2. candidate overlay 的 RTL/support 集合必须精确匹配 lock，不能通过 support file 注入额外 HDL。
3. configure 前清除 `obj_dir/output/tmp/case_obj/software obj/log/config`，构建产物必须晚于本轮 build 起点并记录 SHA-256。
4. `%Error`、`%Fatal`、make error、超时、缺失或旧产物都禁止启动 simulation。
5. 官方编译 warning 与构建完整性分开报告。warning 不得被描述为独立 `rtl-static` PASS；有 warning 时整体 gate 仍失败，但在构建完整性成立时允许继续取得功能诊断证据。
6. simulation 必须由 NEMU/DiffTest marker、结束条件、指令/周期数和失败模式 parser 判定；命令返回 0 本身不是 PASS。
7. `SKIP`、未执行、缺少结果文件或 parser 无法判定均视为失败。

## 输出

- doctor、overlay、DUT/support 和官方 workspace 指纹。
- configure/build/simulation 的真实 argv、退出码、超时状态与原始日志 locator。
- 六个构建产物和 trace/UART 文件的新鲜度、大小与 SHA-256。
- 首个 mismatch、PC、指令/周期数、warning 分类和 gate 计数。
- 当前 evaluator、manifest、allowlist、doctor 和 overlay report 的相互哈希绑定。

## PASS 标准

只有以下项目全部成立才可把本边界提升为 `full_regression_pass`：

1. doctor、Scala、candidate overlay 和构建完整性通过。
2. 所有 warning 已修复或存在逐规则、逐文件、逐行的有效 waiver；禁止全局关闭 WIDTH、LATCH、UNDRIVEN、UNOPTFLAT 或 CDC 类告警。
3. 锁定 smoke 功能通过，`executed=1, passed=1, failed=0, skipped=0`。
4. 独立 claim review 无 blocking finding，实验数字通过完整性审计。

当前 `a158aa8` 不满足第 2、3、4 项，因此仍是 blocked candidate。
