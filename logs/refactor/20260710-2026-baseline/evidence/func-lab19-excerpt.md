# `func/func_lab19` exact 失败摘录

- 源码 HEAD：`45043bd8a89b0e4dea3911ed609d128252f0319f`
- chiplab：`a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`
- candidate：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`
- 报告时间：`2026-07-11T14:37:58+08:00`
- 功能计数：planned 1 / executed 1 / passed 0 / failed 1 / skipped 0
- 指令数：`172552`
- 周期数：`602903`
- 首个 mismatch：

```text
t0(r12) different at pc = 0x1c07c79c, right= 0x000006e2, wrong = 0x00000008
this_pc different at pc = 0x1c07c79c, right= 0x1c07c79c, wrong = 0x1c07c7a4
Both Error(Code:0x700)
```

Verilator 构建产物新鲜度检查通过，但 warning policy 失败：DUT 280 条、官方环境 364 条，共 644 条未获批准 warning。三个子命令退出码均为 0；最终 gate 仍由结果 parser 正确判为失败。

原始日志不提交 Git，绝对 locator 与 SHA256 见 `rtl-smoke-summary.json.commands`；完整 trace、可执行文件和 Vivado/仿真大产物继续保存在 WSL artifact 目录。
