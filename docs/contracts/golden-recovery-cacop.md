# Golden recovery / CACOP 行为合同

## 目标

定位 `d22c13c` 到 `a158aa8` 之间导致官方 `func_lab19` 在 `0x1c07c79c` 首错的 CACOP 回归，并形成可执行的最小修复证据。本边界只处理功能正确性，不做 cache 性能优化，也不更新锁定 reference。

## 固定输入

- chiplab：`a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`
- myCPU gitlink：`aa3bde1f3e720e71c2c78d6b81930d797b810149`
- 通过候选：`d22c13c1ecbee7b0423b7e4f4616f24d98457f02`
- 已知失败：`d76ca40be528eb8de6e258d1ba249a44eaaed6b6`、`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`
- 工具版本和哈希：`reference/manifest.lock`

## 不变量

1. 历史提交只通过 diagnostic overlay 比较，不得改写 `team_golden_candidate` 或冒充 locked baseline。
2. 每个历史点使用独立 chiplab worktree/evidence root，记录 DUT blob、命令、退出码、首错和 trace 哈希。
3. CACOP 请求不得产生与体系结构语义不一致的 cache line；命中/未命中、mode、tag/valid/dirty 更新和 AXI 副作用必须可观察。
4. 修复必须同时检查活动 Spinal I/D Cache；不得只改历史 Verilog oracle而让当前活动 core 保留同一缺陷。
5. `func_lab19` 单例通过只支持该回归边界，不代表 58/81、random、perf、Linux 或 FPGA 通过。

## 最低门禁

- 历史提交二分 smoke；
- CACOP 定向测试与负控；
- Scala/生成/端口/Yosys/严格 lint；
- 当前活动 `core_top` 官方 smoke；
- 独立 claim review 与 experiment audit。

锁定 reference 的更新属于单独人工确认 PR，本迭代不得修改 `reference/manifest.lock`。
