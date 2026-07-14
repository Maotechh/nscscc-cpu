# 独立只读审核原文

审核目标：`2e5409a73841424540978e8dc43f6ba8b576a31e`

## Accepted

- 仅声明以下内容有充分证据：
  - `2e5409a` 修复了 `0x1c0752b8` 连续 store 的伪 forwarding 回归。
  - candidate 在 `func_lab19` 到达锁定 baseline 相同的首个架构 mismatch：`0x1c07c79c`。
- Scala gate 为 25/25 PASS；证据中的 74 个 Spinal 源文件哈希与当前 HEAD 全部一致。
- 新 smoke 使用 `2e5409a` 已提交 blob，overlay 工作树干净。
- 已独立复算两份原始 trace：文件 SHA256 与 evidence 一致；首个 mismatch、r12、next PC 一致；归一化末 30 行逐行相同，SHA256 均为 `757266c1754c435d5ebae2d1c240a11ba57a8293fe78449081c8743f2427fea8`。
- artifacts 索引中的 Scala、smoke、comparison、diagnosis 哈希均正确。

## Fixed

- 先前 MEM forwarding 测试与 Scala evidence 哈希不一致的问题已闭合。
- 修复后官方 smoke 已实际运行，不再停在旧 forwarding 首错。

## Open

- Scala evidence 的 `repo_head_sha` 仍为 `39501d1`，但完整源码快照精确匹配 `2e5409a`。必须显式保留这一 provenance 限制。
- baseline 与 candidate 的提交计数相差 4，周期数也不同，不能声明完整顺序 trace 等价或整机等价。
- `func_lab19` 和严格 lint 仍为 FAIL。
- Claude bridge 两次失败，只能记录降级审核，不能表述为 Claude 审核通过。
