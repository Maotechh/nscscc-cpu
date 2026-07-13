# 20260713-0729-exe-stage-spinal

- Status: implementation_in_review
- Branch / Base SHA / Head SHA: `refactor/20260713-0729-exe-stage-spinal` / `f621c7a1e056b9f128b86efddbdd2598b3692ecc` / `4c73068aad5a81b34181138b20184f894016f327`（实现与受测提交；本日志为其直接证据提交）
- Owner / Agent: execute / exe_stage_spinal
- 选择边界及理由：EXE 是 ALU、mul/div、访存请求、TLB/CACOP/PRELD 与 MEM 握手的首个整级交汇点；先迁移该级可以把已验证叶子接入活动流水线，同时保留旧 top 回退路径。
- Golden 与锁定工具：`a158aa8:rtl/exe_stage.v`，SHA256 `cab20e05205c6bddff19f01fd15ad4cb671144debf0836982b45b334c686f526`；Scala 2.13.16、SpinalHDL 1.14.2、Verilator 5.020、Yosys 0.33、Vivado 2023.2。
- 行为合同：`docs/contracts/exe-stage.md`；精确 legacy 端口见 `reference/component-contracts/exe-stage-ports.json`。
- 修改内容：directionless typed `ExecuteStage`、显式同步 ClockDomain 的 `LegacyExecuteStage`、LACC off/on 生成器、端口/替换 manifest、Verilator 锁步和负控工具、非 LACC committed replacement RTL、Makefile 入口。
- 失败与修复：首轮 Scala 有 2 个 UInt 类型错误；首轮生成器未消费 `--out-dir`；首轮锁步暴露 store mask/data 优先级和 ALE 门控问题，均按 golden 位级合同修复。一次把 off RTL 用于 on 端口检查的命令错误已纠正，之后改为 profile 绑定的独立生成物。
- 门禁结果：仓库自动化 304/304；Scala format/compile/test-compile/test 4/4；off/on 生成各 2/2 可复现；端口、候选 Verilator lint、Yosys hierarchy/proc/check 各 profile 全通过；golden/candidate 锁步各 8192/8192；两 profile 负控均在 cycle 0 检出 mismatch；Windows doctor 19/19（含 Vivado ML Standard 2023.2 probe）。证据见 `evidence/`。
- Warning 处理：锁步编译报告的 16/25 条 warning 全来自锁定 golden、ALU、工具或随机测试台；候选 RTL 独立 `-Wall` 为 0 warning，任何候选 warning 会使脚本失败。未将 harness warning 宣称为 DUT 零 warning。
- chiplab：在 WSL ext2/ext3 上从本地锁定对象建立干净 reference；doctor 对 chiplab `a2e11b3...`、myCPU `aa3bde1...`、真实 symlink 和全部工具/包哈希检查通过。提交绑定的 mixed overlay 只替换 `rtl/exe_stage.v`。官方 `func_lab19` 执行 1/1、通过 0/1：172552 条指令、602903 周期后仍在 `0x1c07c79c` 首错，架构 trace SHA256 `8efa7942...` 与 locked baseline 完全一致。该结果只说明首错前行为未变化，不是功能 PASS。整机编译仍有 278 条 DUT 和 364 条官方环境 warning，严格 warning gate 失败。
- Claim 审核：共三次调用 `claude-review`。job `318317...` 与 `8e3d87...` 因 bridge 进程未继承 `GEEKPIE_CLAUDE_API_KEY` 在模型启动前失败；job `03e7f7...` 因 responses 后端禁止 reviewer tools 失败。原始事件均已记录；独立只读复核与实验性 claim 审计单独标注，不能称为 Claude 通过。
- 功能/性能/资源：本迭代只声明 EXE 单模块 2-state 逐拍差分；未运行性能、完整功能集、随机 DiffTest、U-Boot/Linux 或 Vivado implementation/timing/bitstream。
- 残余风险：LACC 历史 `lacc_flush` 在 golden 中未驱动，重构保持确定性 0，仅有 2-state 输出一致证据，不代表四态等价；整机 MEM/CSR/TLB/cache 等仍有 legacy 实现；mixed warning policy、func_full、随机 DiffTest 和 golden 顺序形式等价均未通过。
- 回退：revert 本迭代提交，或删除 replacement spec 中 `rtl/exe_stage.v` overlay；旧 Verilog 保持为参赛稳定线。
- PR 状态：证据提交后推送分支；不创建或合并 PR。
- 下一候选：把已独立审核的 EXE、CSR、AddrTrans、AXI 和 cache replacement 放入非 main staging overlay，随后迁移 IF/ID/MEM/WB 活动流水级。
