# 独立只读审查

审查目标：`9e78538c0dec08fa9fcace49e068b8bc9d4d5af1`。两个独立代理分别检查实现时序与 gate 失效策略；本文件不是 Claude 审核。

## 实现与时序

- 未发现功能性 blocking 或 major finding。
- `OpenLa500Div` 在锁定的 2-state 合法 held-request 合同内保留同步复位、E33/E34/E35/E36、符号缓存、late abort、除零和有符号溢出轨迹。
- E33 的 `complete` 与商有效、历史余数，E34 的最终余数和 held-high cleanup/restart 均由逐拍测试覆盖。
- 允许的声明必须限定为 4136 个合法 held-request transaction 的合同窗口；不得扩大为所有 invalid window 或完整顺序形式等价。

## Gate 与 provenance

审查提出四项非阻塞问题：

1. 删除未使用且易误导的 `expected_compile_pass` 参数：已在 `9e78538` 修复。
2. formal 负控必须出现精确 SAT counterexample，且拒绝额外 `ERROR:`：已在 `9e78538` 修复并重跑 3/3。
3. candidate summary 补 repository HEAD、manifest、evaluator、driver 与 vectors provenance：已在 `9e78538` 修复并重跑 4136/4136。
4. 未知 Make `TARGET` 目前由字符串单测覆盖：另行实际执行 `make generate TARGET=typo`，观察到退出码 2；后续可把该进程级检查纳入自动化单测。

Verilator 为规避合法的“模块名 `div` 与端口名 `div`”C++ 后端冲突，只在 lint 私有快照中把唯一模块声明改名为 `div_lint`。精确端口、Yosys、formal 和差分均消费未改名的原始 committed RTL。

## 结论

当前实现可进入 `differential_pass`，但 PR 保持 Draft。`func_lab19`、warning policy、Vivado 严格门禁与 Claude 审核均未通过；不允许提升为 `integrated_pass`。
