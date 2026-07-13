# 独立本地只读审核

审核代理只读检查了 `reference/core-top.ports.json`、Spinal compatibility wrapper、`tools/core_top_gate.py` 和 fresh gate evidence，未修改 worktree。

## Accepted

- 49 端口（17 input、32 output）合同由两个锁定 Git object 的 blob/raw/header hash 支持。
- AXI3/WID、8-bit `arlen/awlen` 和 debug 端口的接口形状与 49/49 同名透明连接有 Yosys 证据。
- `TLBNUM=32` 的 top 默认值、backend 符号转发和唯一 backend cell 有结构证据。
- clock/reset 只可声明为锁定 metadata、显式 ClockDomain 声明和 raw `aclk/aresetn` 透传；不能外推未来状态等价。

## Fixed

- 原 loader 只要求 `clock_reset` 字段存在，不检查值。现已用 `EXPECTED_CLOCK_RESET` 精确比较，并以 falling edge、active-high reset 和 1-cycle wrapper latency 三种 mutation 证明负控生效。
- 修复后用 fresh OUT_DIR 重跑 contract、generate、package、publish、port、lint、Yosys，所有 summary 绑定 evaluator SHA256 `4424290fdb8d6da65764b7f701bf19cbd71c44b9d4d214f6dc3843c3f3d9a3fb`。

## Open

- wrapper lint/Yosys 使用 synthetic backend stub，不是完整 package 的官方 chiplab compile。
- 没有动态 reset、AXI 或 debug 行为测试；结构透明性不代表事务或提交语义等价。
- Claude bridge 未启动，不能提升为 ready。

## 禁止声明

不得声明完整 package 静态通过、整机功能、reset 状态等价、AXI/debug 行为等价、58/81、random DiffTest、perf20、U-Boot/Linux、Vivado implementation/bitstream、Scala 唯一手写真源或完全重构。
