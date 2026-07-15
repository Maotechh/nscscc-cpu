# 独立只读代码与证据审查

审查代理：`/root/mul_final_audit`。这不是 Claude 审查。

审查首先针对 `dea1b95` 的实现与日志，发现七项问题：

1. 门禁命令错误记录 `RTL=`，而 Makefile 实际消费 `MUL_RTL=`。
2. Vivado Tcl 名称、argv 和耗时与原始 summary 冲突，且漏记 path/netlist 诊断。
3. 所有 PASS 当时仍是 pre-commit 证据。
4. contract 未进入机器可读 required gate。
5. external artifact 不受 `evidence-check` 哈希复核。
6. candidate unit 直接编译可变源路径，存在 change-and-restore TOCTOU。
7. automation/chiplab 命令没有完整记录解释器或显式环境。

上述问题均接受。代码侧在 `f6c55e6` 加入 hash snapshot、source/snapshot 前后复核、
contract evaluator provenance 和负向测试；随后从 clean LF clone 重跑全部门禁。日志侧恢复
原始 Vivado argv/耗时、使用 `MUL_RTL`、增加 contract gate，并把紧凑证据纳入
`artifacts.json` 的 tracked hash 校验。

仍未解决的是外部结论：Claude bridge 不可用、golden 完整形式等价未证明、官方
`func_lab19` 与 640 条 warning 失败、Vivado 63 条 warning 未批准。降级审查不能把这些
阻塞改写成 PASS。
