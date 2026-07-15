# 20260715-1230-pure-overlay-profile

- 状态：`draft`
- 分支 / Base SHA / 当前 Head：`refactor/20260714-1650-consolidated-spinal` / `df25f38153373150c757fa1503ea433a55414aee` / `df25f38153373150c757fa1503ea433a55414aee`（提交后回填）
- 选择边界：把 candidate-closure 检查接入官方隔离 overlay 的 diagnostic profile，验证只保留 self-contained Spinal `mycpu_top.v` 是否能被 chiplab 原生入口编译和运行。
- 本轮新增 `--pure-spinal`：仅允许 diagnostic mixed source；临时 `IP/myCPU` 删除旧 CPU HDL，保留生成 top、`mycpu.h` 和 LICENSE；manifest 记录删除清单和单文件选择 hash。默认 candidate/mixed profile 不改变。

## 证据

- 代码先通过 `python -m py_compile` 和 `make test-automation`（381 tests passed, 10 skipped）。
- chiplab doctor、pure overlay、candidate-closure、native compile/smoke 结果待提交后在 clean clone 运行并复制到 `evidence/`。

## 风险与回退

- pure profile 是 diagnostic，不具备 gate-eligible release 资格；若官方 Makefile 隐式依赖旧文件，命令必须失败并记录，不删除 locked 默认输入。
- 回退：revert 本迭代提交即可移除 `--pure-spinal`，默认 overlay 行为不变。
- Claude bridge 需在运行后调用；缺 key 时保持 unavailable，不伪造审核。
