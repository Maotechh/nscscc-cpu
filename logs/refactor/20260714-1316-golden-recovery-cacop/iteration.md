# 20260714-1316-golden-recovery-cacop

- Status: `implementation_in_review`
- Branch / Base SHA / Source HEAD: `refactor/20260714-1316-golden-recovery-cacop` / `13e0c8da423bb75ca848aada91c67738f22a60ab` / `pending`
- Owner / Agent: Codex
- Selected boundary and reason: `baseline_validation/cacop`。锁定 baseline 与当前 Spinal core 均在 `0x1c07c79c` 失败；已有矩阵将首次失败缩到 CACOP cache-hit 改动，先恢复可执行 oracle 才能继续扩大等价声明。
- Golden reference and locked tools: `reference/manifest.lock`；Vivado 2023.2。

## 行为合同

见 `docs/contracts/golden-recovery-cacop.md`。本轮不更新 lock、不做性能优化、不自动创建或合并 PR。

## 当前证据

- `d22c13c` 的历史 diagnostic smoke 曾通过 parser。
- `d76ca40` 把 I/D Cache 的 `cache_hit` 改为 CACOP 无条件命中；`func_lab19` 随后在 `0x1c07c79c` 失败。
- 后续 `2ffb1ab` 改为 FSM bypass，`40830b8` 增加 CACOP `data_ok`，最终 `a158aa8` 仍在同点失败。
- 上述中间提交尚未在本迭代的固定环境中逐点复测，暂不作根因结论。

## 尝试与失败

待记录。

## 门禁结果

待执行。任何 skip 或未执行项均不算 PASS。

## 残余风险

- 锁定 baseline 当前不是通过的 golden truth。
- 当前活动 Spinal I/D Cache 复制了 `a158aa8` 的 CACOP bypass 语义。
- 严格 lint、完整功能、random、perf、Linux 和 FPGA release gate 未闭合。
- Claude bridge 当前缺少 `GEEKPIE_CLAUDE_API_KEY`。

## 回退与 PR

- 回退：revert 本迭代提交；不修改或合并 `main`。
- PR：`awaiting_push` / draft；代理不自动创建或合并 PR。
