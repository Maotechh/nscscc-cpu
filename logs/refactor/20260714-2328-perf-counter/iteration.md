# 20260714-2328-perf-counter

- 状态：`implementation_in_review`
- 分支 / Base SHA / Head SHA：`refactor/20260714-1650-consolidated-spinal` / `5038a537a02c1778a13ceca6b07d26e311b9afd6` / `b015be13f468d34debc912e77db8b8423e846a98`
- 选择边界：`observe/perf_counter`。它是活动 core_top 中行为独立、可建立 golden lockstep 且影响面较小的状态叶子。
- 行为合同：`docs/contracts/perf-counter.md`；机器合同：`reference/component-contracts/perf-counter.json`。
- 已完成：七类 writeback event 接入 `OpenLa500PerfCounter`；legacy 九端口生成器、typed snapshot、module-free runtime overlay、2/2 可复现生成和 8192 周期差分均通过。
- Scala 门禁：scalafmt、compile、test-compile、test 全部通过，31/31 tests PASS；证据在 `build/perf-counter-scala-final-2/scala-check/`。
- RTL 静态门禁：legacy port-check、候选 lint、Yosys hierarchy/check 均通过。整机严格 lint 仍有既有 warning（LACC-off 73，LACC-on 74），不能宣称 whole-top lint PASS。

## 官方 chiplab 闭环

- 环境：chiplab `a2e11b38bc5c85abb4408a8e0c0f5ce903c7ba31`，myCPU gitlink `aa3bde1f3e720e71c2c78d6b81930d797b810149`，JDK 17.0.19，Verilator 5.020，Yosys 0.33；`chiplab-doctor` PASS。
- 隔离目录：`/tmp/nscscc-perf-counter-work/20260715-0118-perf-counter-diagnostic`；摘要证据复制到 `evidence/rtl-smoke-20260715-0118/`。
- overlay 使用完整 source SHA，替换 5 个锁定 blob；overlay 为 diagnostic/mixed provenance，不能作为 candidate-locked release gate。
- `configure.sh --run func/func_lab19`、`make verilator testbench soft_compile`、`make simulation_run_prog` 分别返回 0。
- parser 观察到 `instructions=174069`、`clocks=609803`、`first_mismatch=null`、`difftest_enabled=true`，但 `good_trap=false`，UART 输出为空；因此 `func_smoke` FAIL。
- warning policy FAIL：DUT 237 条、官方环境 364 条，尚无逐文件 waiver。失败不是 perf_counter leaf 差分失败，而是整机基线/警告策略问题，需单独隔离处理。

## 审核与风险

- Claude bridge 因缺少 `GEEKPIE_CLAUDE_API_KEY` 未执行；已记录为 unavailable，不把独立审查冒充 Claude 审核。
- 不支持“官方 smoke PASS”“整机完成”或“release ready”声明。58/81 功能、random DiffTest、perf20、U-Boot/Linux、Vivado 尚未通过。
- 回退：revert 本迭代提交即可恢复 perf_counter 的旧 backend 接线，不删除锁定 golden。
- PR 状态：`awaiting_pr`；只推送分支，不自动创建 ready PR，也不合并 `main`。
