# Draft PR：锁定最新 Spinal core_top 发布物并增加 candidate closure 门禁

## 变更

- 使用当前 Scala/官方 32-entry predictor 重新生成并提交 `reference/component-replacements/mycpu_top.v`。
- 同步 `core-top.json`、`active-reachable.json`、`spinal-active-runtime.json` 的 replacement SHA256。
- 新增 `make candidate-closure` 和 4 个正负测试，证明生成层级没有旧 CPU Verilog module 定义/实例。
- 修订中文迭代日志、状态事实源和 memory/observability/candidate-closure 合同。

## 证据与限制

- Scala、2/2 reproducible generation、49-port package、publish-check、candidate hierarchy closure：PASS。
- 官方旧 Verilog overlay 尚未删除；pure overlay、func-full/random、perf20、U-Boot/Linux、Vivado 和完整 DiffTest 仍未通过。
- Claude bridge 缺少 `GEEKPIE_CLAUDE_API_KEY`，PR 保持 draft/awaiting_pr。

## 回退

revert 本 PR 可恢复旧 tracked package 和新增门禁；不修改 `main` 或官方 chiplab clone。
