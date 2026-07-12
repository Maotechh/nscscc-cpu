# Draft PR：建立官方 core_top 兼容边界

状态：`wrapped_golden / draft / awaiting_push`。两次 GitHub push 因网络 timeout/reset 失败；不自动创建、标记 ready 或合并 PR。

本 PR 建立精确 49 端口的 SpinalHDL `CoreTopCompat`、锁定工具链的可复现 generator，以及只允许机械改名的 legacy 迁移后端。它固定官方 AXI3/WID、interrupt/debug 和 `aclk/aresetn` 边界，但不声称流水、特权、存储或整机已经迁移。

Commit-bound `0e2787f` 已通过 296 项自动化、Scala 4/4、双生成、publish consistency 和 wrapper-only port/lint/Yosys。locked/mixed `func_lab19` 均在 `0x1c07c79c` 失败，trace/计数相同但 warning 为 644/635，identity gate FAIL。Vivado 完成 synth/implementation/timing/bitstream，WNS `+0.364214 ns`，但 46 个未批准 DRC warning 使 strict FPGA gate FAIL；未提交远程板卡 job。

功能、perf20、58/81、random、U-Boot/Linux 均无通过证据。Claude bridge 在模型启动前缺少 API key。回退为 revert 本迭代提交并恢复上一分支 overlay；保持 draft，不自动创建或合并 PR。
