# 独立只读 Claim 审核

本审核由独立 Codex 子代理完成，不是 Claude 或其他模型家族的跨模型审核。受测实现为 `75523504912c1b390dc1d1e3cddb5c3a0cc43a27`。

## 结论

- `scala.json` 支持 format/compile/test compile/test 4/4 通过及 ScalaTest 25/25 通过。
- 两次生成可复现；package/publish、49 端口和 Yosys 通过，发布 RTL SHA 为 `27b578ce4bf3c3157b65d2e05e2b45603da6e67e776a79a93630bede8981c6c0`。
- chiplab doctor 通过，锁定 commit、工具版本和哈希匹配。
- 最终 `func_lab19` mixed diagnostic 的功能 parser 通过：174034 条指令、610132 拍、DiffTest 已启用并加载、无 mismatch、到达 `END by Syscall`。
- smoke 总 gate 失败：DUT 258 条、官方环境 364 条编译 warning 未获逐项豁免；`gate_eligible=false`、`baseline_exact=false`、`candidate_locked=false`。
- standalone lint 只支持“失败”结论；其摘要没有可复核的精确 warning 计数。

## Claim 限界

- `accepted`：Scala、可复现生成、package/publish、端口、Yosys 和 doctor 的窄门禁结果。
- `partial`：单个 mixed diagnostic `func_lab19` 未再观察到旧 branch replay mismatch；这不证明唯一根因。
- `rejected`：official smoke gate PASS、完整 BTB 等价、完整 Spinal 重构或整机顺序等价。
- `open`：独立 BTB 定向 harness、64-entry/2-bit/RAS、58/81、random、perf、Linux、Vivado 和 formal。

Draft PR 可以保留，但不能 ready 或 merge。
