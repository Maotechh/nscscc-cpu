# Draft PR：增加 locked golden 的逐组件 diagnostic overlay

## 状态

`awaiting_pr`。实现和本地证据已推送，但官方 smoke 失败、独立 rtl-static 未运行、Claude 不可用；因此即使创建也只能保持 Draft。按用户要求当前不自动创建 PR，不允许代理自动合并。

## Base / 分支 / 日志

- Base：`fec3e1460fb9658329d5221e062c116090ef4d99`
- Branch：`refactor/20260711-1533-component-overlay`
- Reviewed source HEAD：`71a1995b7ca4dd922d1896e6b820e8029ff88575`
- 日志：`logs/refactor/20260711-1533-component-overlay/`

## 目标

在不复制完整历史 RTL、不修改 locked baseline 默认语义的前提下，为一个已提交 component replacement 建立结构化、fail-closed、可追溯的 chiplab diagnostic overlay。report 只有在协作锁内写入并由 publication marker 绑定后才能被消费；consumer 复算物理 artifact/raw log、marker、source 和 locked reference。

## 验证结果

- Windows doctor 19/19；WSL chiplab doctor 44/44；Scala 4/4。
- Windows 自动化 123 PASS/8 SKIP；WSL 自动化 101/101 PASS。按 skip 规则，跨主机自动化正式 gate 仍记失败。
- locked 与等字节 ALU mixed overlay 均成功。
- 两侧 `func/func_lab19` 均失败：172552 instructions、602903 cycles，首错 PC `0x1c07c79c`，`t0` expected `0x000006e2` / actual `0x00000008`。
- identity comparator `status=pass`、`gate_eligible=false`，只证明单用例选定失败观测一致；不证明功能正确或 RTL 等价。
- 独立 rtl-static/Yosys、性能、Linux、FPGA 未执行；Claude bridge 在模型启动前失败。

## 非目标

- 不修复 cacop 或迁移 CPU 模块。
- 不更新 `team_golden_candidate`。
- 不允许 mixed overlay 报告 `candidate_locked=true` 或 `gate_eligible=true`。
- 不声明功能、性能、Linux 或 FPGA gate 通过。

## 回退

revert 本 Draft PR；locked candidate 的原有命令和输出必须保持兼容。

## 资源与性能

本迭代不修改 DUT，不做性能优化。未运行 Vivado synth/implementation，因此没有 Fmax/LUT/FF/BRAM claim。
