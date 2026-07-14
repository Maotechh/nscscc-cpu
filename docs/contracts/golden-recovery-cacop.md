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

### d22 定向逐拍门禁

本迭代使用 `tools/cacop_recovery_gate.py` 将 `d22c13c1ecbee7b0423b7e4f4616f24d98457f02`
作为仅限 CACOP recovery 的逐拍 oracle。脚本在自身固定该提交以及 I-cache、D-cache、helper RTL 的
Git blob SHA1，不读取或修改全局 `team_golden_candidate`。固定向量先通过普通 miss/refill 在同一 index
建立 way 0/1，再覆盖 mode 0/1/2/3、两路选择、mode 2 hit/miss、Replace 的 `rd_rdy` backpressure、
无读请求 refill 的单拍 tag invalidation，以及 D-cache dirty mode 1/2 writeback。

同一向量必须识别以下历史负控，缺少任一负控差分即 fail closed：

- `d76ca40be528eb8de6e258d1ba249a44eaaed6b6`：CACOP 被并入普通 `cache_hit`；
- `2ffb1abe4e23eb2272c1b0f899a4ef0727994e05`：lookup CACOP bypass；
- `40830b8307be27128cb215dc4ea66908bd128334`：CACOP 立即 `data_ok`。

运行入口：

```bash
make cacop-recovery-unit \
  CACOP_RECOVERY_REPO=<read-only-git-source> \
  ICACHE_RTL=<generated-icache.v> \
  DCACHE_RTL=<generated-dcache.v> \
  OUT_DIR=<fresh-output-root>
```

该门禁通过只支持“候选在所列定向轨迹上与 d22 CACOP 行为一致”，不支持完整 cache、func、
DiffTest、性能、Linux 或 FPGA claim。
