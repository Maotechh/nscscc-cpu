# nscscc-cpu

本仓库正在把 NSCSCC 2026 参赛 CPU 从历史 openLA500 Verilog 渐进重构为 SpinalHDL。当前尚未完成纯 SpinalHDL 重构，也没有通过完整官方回归。

## 当前事实

- 行为候选基线固定为 `a158aa8`，但它在锁定 chiplab 的 `func/func_lab19` 上存在已复现 mismatch，因此不是已证明正确的 golden truth。
- 当前 `main` 生成的 `CPUCoreFlat` 不是官方 `core_top` 兼容实现，不能作为重构完成证据。
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
```

缺失的 gate、非零退出、`SKIP` 或手写 PASS 文本均不构成功能完成。
