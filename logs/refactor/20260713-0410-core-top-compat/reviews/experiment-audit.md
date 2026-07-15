# 实验与 Claim 完整性审计

- 状态：`pass_with_scope_warnings`
- 审核者：独立只读 Codex 子代理（降级路径，不是 GPT-5.4/Claude cross-model）
- 提交：`0e2787fc5ab30e246da5be1c6080e2847b2645cf`

审计逐个打开 automation、Scala/generator、chiplab 和 Vivado 原始文件，复核了测试数量、哈希、首错、周期、warning、run status、timing、资源和 bitstream。没有发现 phantom result、伪造哈希或声称存在但实际缺失的结果。

需要保留的范围限制：

- 296 是 Python 单元测试，不是 RTL 功能项。
- 49-port/Yosys 结果是 `compat-wrapper-only`，不是完整 legacy package 静态 PASS。
- locked/mixed 都是功能失败；相同 trace 只支持单个失败轨迹观测相同。
- Vivado 官方 Tcl 完成 synth/implementation/timing/bitstream，但 post-route DRC 有 46 warning，batch log 共有 155 warning line，且仓库尚无 `make rtl-fpga` 机器入口；strict FPGA gate 不支持 PASS。

两处 locator 写法已更正：Windows doctor 在 `reports/doctor.json`；`bit-short.log` 在 `fpga/nscscc-team/run_vivado/`。原始大 artifact 仍位于 `/tmp` 和 `.work`，Git 只提交摘要、哈希与 locator。
