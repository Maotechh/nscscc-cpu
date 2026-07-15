# 20260713-0729-exe-stage-spinal

- Status: implementation_in_review
- Branch / Base SHA / Head SHA: `refactor/20260713-0729-exe-stage-spinal` / `f621c7a1e056b9f128b86efddbdd2598b3692ecc` / 待提交
- Owner / Agent: execute / exe_stage_spinal
- 选择边界及理由：EXE 是 ALU、mul/div、访存请求、TLB/CACOP/PRELD 与 MEM 握手的首个整级交汇点；先迁移该级可以把已验证叶子接入活动流水线，同时保留旧 top 回退路径。
- Golden 与锁定工具：`a158aa8:rtl/exe_stage.v`，SHA256 `cab20e05205c6bddff19f01fd15ad4cb671144debf0836982b45b334c686f526`；Scala 2.13.16、SpinalHDL 1.14.2、Verilator 5.020、Yosys 0.33、Vivado 2023.2。
- 行为合同：`docs/contracts/exe-stage.md`；精确 legacy 端口见 `reference/component-contracts/exe-stage-ports.json`。
- 修改内容：directionless typed `ExecuteStage`、显式同步 ClockDomain 的 `LegacyExecuteStage`、LACC off/on 生成器、端口/替换 manifest、Verilator 锁步和负控工具、非 LACC committed replacement RTL、Makefile 入口。
- 失败与修复：首轮 Scala 有 2 个 UInt 类型错误；首轮生成器未消费 `--out-dir`；首轮锁步暴露 store mask/data 优先级和 ALE 门控问题，均按 golden 位级合同修复。一次把 off RTL 用于 on 端口检查的命令错误已纠正，之后改为 profile 绑定的独立生成物。
- 门禁结果：仓库自动化 304/304；Scala format/compile/test-compile/test 4/4；off/on 生成各 2/2 可复现；端口、候选 Verilator lint、Yosys hierarchy/proc/check 各 profile 全通过；golden/candidate 锁步各 8192/8192；两 profile 负控均在 cycle 0 检出 mismatch；Windows doctor 19/19（含 Vivado ML Standard 2023.2 probe）。证据见 `evidence/`。
- Warning 处理：锁步编译报告的 16/25 条 warning 全来自锁定 golden、ALU、工具或随机测试台；候选 RTL 独立 `-Wall` 为 0 warning，任何候选 warning 会使脚本失败。未将 harness warning 宣称为 DUT 零 warning。
- chiplab：实现提交前未运行 overlay；后续在干净提交上执行锁定 chiplab doctor、隔离 overlay 和官方 `rtl-smoke`。由于已知 `func_lab19` baseline 在 `0x1c07c79c` 失败，不能把 smoke 结果写成功能 PASS。
- Claim 审核：`claude-review` job `318317eda1234ab1bd00711454c02053` 因缺少 `GEEKPIE_CLAUDE_API_KEY` 在模型启动前失败；已原样记录并完成本地独立只读复核，不能称为 Claude 通过。
- 功能/性能/资源：本迭代只声明 EXE 单模块 2-state 逐拍差分；未运行性能、完整功能集、随机 DiffTest、U-Boot/Linux 或 Vivado implementation/timing/bitstream。
- 残余风险：LACC 历史 `lacc_flush` 在 golden 中未驱动，重构保持确定性 0，仅有 2-state 输出一致证据，不代表四态等价；整机 MEM/CSR/TLB/cache/AXI 仍未迁移；golden 顺序形式等价尚未证明。
- 回退：revert 本迭代提交，或删除 replacement spec 中 `rtl/exe_stage.v` overlay；旧 Verilog 保持为参赛稳定线。
- PR 状态：待提交、待推送；不创建或合并 PR。
- 下一候选：先在干净提交完成 chiplab mixed 诊断，再迁移 MEM/CSR/TLB，并以 EXE typed contract 作为依赖。
