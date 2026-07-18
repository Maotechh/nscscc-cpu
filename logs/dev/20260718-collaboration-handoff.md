# dev 协同开发交接（2026-07-18）

## 接受的硬件状态

当前 checkpoint 只接受迭代 002/003 的两项低风险优化，BTB 64/128 容量实验已经完整回退：

1. 非分支、非共享乘除/LACC 消费者可把尚未完成的 EX 结果标记为 late-forward，在 EX 等待下一拍 MEM 结果，消除固定的 Decode 空泡。
2. Decode 级分支/JIRL 可直接消费已经完成的 MEM 前递结果；redirect 只在 Decode 与 EX 真正握手时发出。

正式发布 RTL 为 `rtl/mycpu_top.v`，SHA-256 为 `b51160dfeaafbec3784e485f79d1a05b97e3f0083de632280b18d8a436c9c5fd`。它完全由锁定 Scala/SpinalHDL 生成并经 package gate 机械注入兼容头和局部 lint 注解，没有手写 Verilog。

## 已有证据边界

- 锁定 Scala 门禁：格式、编译、测试编译、19 suites / 33 tests 全通过。
- Python 自动化：398 tests 全通过。
- 正式 package/publish-check：fresh RTL 与提交候选逐字一致。
- 静态：49 端口、严格零 warning Verilator、Yosys、typed AXI、candidate closure、replacement reachability 全通过。
- 本地 func_lab19：同字节硬件快照 19/19 通过。
- 本地 perf20：20/20 DiffTest；计分周期 39,461,758，总周期 52,267,170，相对迭代 002 为 1.04445x，相对迭代 001 前状态累计约 1.05417x。
- 同字节 Vivado 快照：WNS +0.410125 ns、TNS 0、22,977 LUT、23,790 registers、36.5 BRAM、8 DSP。
- 真实板卡：有效样本仍为 0/3；已有远端任务因外部 JTAG 锁占在编程阶段结束，不能宣称功能满分或真实板性能改善。

上述 Vivado/功能证据绑定的是字节等价评测快照。协同 checkpoint 提交后必须用新的 40 位 commit 再生成 commit-bound 包；不能把旧包描述成新提交的直接证据。

## 保守编译含义

受限 FPGA 客户端固定使用 `Flow_PerfOptimized_high` 综合和 `Performance_Explore` 实现，不提供合法的 Area/Conservative strategy 参数。不得修改客户端 Tcl 绕过锁定流程。本次“保守性能占用”指恢复官方 32 项 BTB 并使用标准锁定策略，而不是提交 128 项高占用候选。

## 已清理内容

为建立干净协作边界，已删除约 46.4 MB 未跟踪原始证据：`dse_results/` 和 `logs/dev/evidence/`。这些文件未进入 Git，不能从仓库恢复；决定性结果已浓缩在五份 Markdown 记录中，外部 `.fpgajob` 仍由本机 FPGA 客户端保存。对应目录已加入 `.gitignore`。

## 下一步可并行任务

1. `branch-ex-resolution`：仅把依赖未完成 EX/MEM 结果的 branch/JIRL 延后到 EX 决议。画像上限约 5.33%，预期 1.03–1.05x。
2. `issue-width-oracle`：从 perf20 ELF/提交轨迹计算双发射、三发射 ILP 上界和 lane 利用率，先量化再改 RTL。
3. `asymmetric-dual-issue`：复用 ICache 内部 128-bit 行，增加 8 项取指队列；副槽只允许无异常纯 ALU，保持内存/CSR/分支/异常单发射。
4. `forwarding-verification`：补 late-forward 的 K/rd、双操作数同源、异常/flush 同拍，以及普通条件分支 MEM 前递定向测试。
5. `board-revalidation`：板卡恢复后对同一 commit-bound perf20 包取得三次有效样本，取最慢一次；再补 func58/func81/random 证据。

全乱序路线建议分阶段引入 ROB、提交时存储、重命名、两 ALU 和 LSQ，不要在一个提交里同时改变精确异常、错误路径存储、MMIO、LL/SC 和分支恢复。
