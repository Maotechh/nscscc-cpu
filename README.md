# nscscc-cpu

本仓库正在把 NSCSCC 2026 参赛 CPU 从历史 openLA500 Verilog 重构为 SpinalHDL。活动 CPU 已由 SpinalHDL 生成一个自包含的 `core_top`，但完整官方回归尚未通过，因此当前分支仍是候选实现而不是比赛稳定版本。

## 当前事实

- 行为候选基线固定为 `a158aa8`，但它在锁定 chiplab 的 `func/func_lab19` 上存在已复现 mismatch，因此不是已证明正确的 golden truth。
- SpinalHDL 活动入口是 `openla500.compat.GenerateCoreTopCompat`，唯一提交的 CPU RTL 生成物是 `rtl/mycpu_top.v`；历史 `CPUCoreFlat` 草稿已移除。
- `rtl/mycpu_top.v` 必须由锁定的 Scala/SBT/SpinalHDL 工具链两次一致生成，并通过 49 端口、发布一致性和候选闭包检查。
- 已有 `func/func_lab19` diagnostic 功能观察不能替代严格 warning、58/81、random、20 perf、Linux 或 FPGA 门禁。
- 变更只允许在 `refactor/*` 分支通过 Draft PR 推进；自动化代理不得合并到 `main`。
- 每次迭代的状态、命令、失败和证据保存在 `logs/refactor/<iteration-id>/`。

权威现状见：

- [`docs/refactor/status.yml`](docs/refactor/status.yml)
- [`docs/contracts/baseline-validation.md`](docs/contracts/baseline-validation.md)
- [`docs/contracts/component-overlay.md`](docs/contracts/component-overlay.md)

工作区级赛题与仓库审计位于本机父目录 `../NSCSCC_2026_AUDIT.md`；该文件不属于 CPU 仓库 PR，不作为远端可解析链接。

## 本地入口

统一入口定义在 `Makefile`。`doctor` 与自动化单测可在 Windows 运行。官方 chiplab 命令必须在 WSL/Linux 的 Linux 文件系统中运行：doctor 显式提供 reference 与 output root；overlay 另提供 iteration 与 work root；smoke 复用同一 output root、iteration 与 work root。

```bash
make test-automation
make doctor OUT_DIR=build VIVADO_HOME='D:/Xilinx/Vivado/2023.2'
make scala-check OUT_DIR=build
make generate TARGET=core_top OUT_DIR=build
make lint TARGET=core_top OUT_DIR=build
make yosys-check TARGET=core_top OUT_DIR=build
```

缺失的 gate、非零退出、`SKIP` 或手写 PASS 文本均不构成功能完成。
