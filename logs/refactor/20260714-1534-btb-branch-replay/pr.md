# Draft PR：绑定 BTB lookup 与已接受 fetch 请求

- Iteration：`20260714-1534-btb-branch-replay`
- Branch：`refactor/20260714-1534-btb-branch-replay`
- Base / tested implementation：`372eccc9b54fb5a80f08bc5af6dcc8944ea3e8fa` / `75523504912c1b390dc1d1e3cddb5c3a0cc43a27`
- 日志：`logs/refactor/20260714-1534-btb-branch-replay/`
- 状态：Draft / blocked；不自动创建、标记 ready 或合并

## 行为合同

lookup 只对上一拍真正接受的 fetch 请求有效；无效或未命中时 target/index 清零，防止 IF 中 lock/current 位或合并污染预测目标。完整合同见 `docs/contracts/btb-branch-replay.md`。

## 验证

- Scala 4/4、ScalaTest 25/25、两次可复现生成、package/publish、49 端口、Yosys、chiplab doctor：PASS。
- strict lint：FAIL。
- 单个 mixed diagnostic `func_lab19`：功能 parser PASS，174034 条指令、610132 拍、无 mismatch；总 gate 1/1/0/1/0，因 DUT 258 和官方环境 364 条未豁免 warning 失败。
- Claude bridge：已调用但缺少 `GEEKPIE_CLAUDE_API_KEY`，没有 reviewer 响应；独立只读子代理只支持窄 claim。
- 58/81、random、perf20、U-Boot、Linux、Vivado release、完整形式等价：未执行。

## 影响与回退

本 PR 不改变公开 `core_top` 端口，未测量 Fmax/LUT/FF/BRAM。当前 predictor 仍是 32-entry direct-mapped always-taken，不是完整 BTB。回退方式是 revert 本迭代三个实现/发布 commit；不得改写或合并 `main`。
