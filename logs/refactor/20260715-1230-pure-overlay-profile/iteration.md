# 20260715-1230-pure-overlay-profile

- 状态：`draft`
- 分支 / Base SHA / 当前 Head：`refactor/20260714-1650-consolidated-spinal` / `df25f38153373150c757fa1503ea433a55414aee` / `e420eba344d45f7333ef2c0a6eb538e850863a8a`
- 选择边界：把 candidate-closure 检查接入官方隔离 overlay 的 diagnostic profile，验证只保留 self-contained Spinal `mycpu_top.v` 是否能被 chiplab 原生入口编译和运行。
- 本轮新增 `--pure-spinal`：仅允许 diagnostic mixed source；临时 `IP/myCPU` 删除旧 CPU HDL，保留生成 top、`mycpu.h` 和 LICENSE；manifest 记录删除清单和单文件选择 hash。默认 candidate/mixed profile 不改变。

## 证据

- 代码先通过 `python -m py_compile` 和 `make test-automation`（381 tests passed, 10 skipped）。
- chiplab doctor：PASS，锁定 commit、gitlink、工具版本和哈希均匹配；证据 `evidence/chiplab-doctor.json`。
- pure overlay：PASS；manifest 只包含 `mycpu_top.v` 一个 HDL，删除 19 个旧 HDL/header 输入，保留 `mycpu.h` 和 LICENSE；profile 为 diagnostic、`gate_eligible=false`。
- candidate-closure：PASS；20 个旧文件名均 absent，生成层级旧模块定义/实例均为 0，RTL SHA256 为 `ded57a4...cad`。
- 官方原生命令：configure、Verilator/testbench/soft_compile、simulation 分别 exit 0；parser 为 `functional_status=pass`、174059 instructions、609660 clocks、syscall 终止、到达 test-end、无首个 mismatch。
- 严格 `rtl-smoke` 仍 FAIL：DUT 40 条、官方环境 365 条 warning 未获批准；本轮不把功能观察 PASS 冒充严格 gate PASS。

## 失败尝试

- 第一次 pure overlay 因旧 `csr.h` 未删除被 manifest 完整性检查拒绝。
- 第二次因清理条件误删 `mycpu.h` 被 required-support 检查拒绝。
- 两个问题均在进入 Verilator 前失败并被修复；第三次 overlay 及完整 smoke 使用 clean clone 和提交 SHA `01c9b21a...`。
- 随后因补充 `pure_spinal` report 字段产生新提交，按 freshness 规则在 `e420eba...` clean clone 再跑 doctor/overlay/closure/smoke；最终证据均来自该 head。

## 风险与回退

- pure profile 是 diagnostic，不具备 gate-eligible release 资格；若官方 Makefile 隐式依赖旧文件，命令必须失败并记录，不删除 locked 默认输入。
- 回退：revert 本迭代提交即可移除 `--pure-spinal`，默认 overlay 行为不变。
- Claude bridge 需在运行后调用；缺 key 时保持 unavailable，不伪造审核。
