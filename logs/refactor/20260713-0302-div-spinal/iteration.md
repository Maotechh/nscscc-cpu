# 20260713-0302-div-spinal

- 状态：`draft / differential_pass`
- 分支：`refactor/20260713-0302-div-spinal`
- Base SHA：`46173cd421f211f8978d27e768297e26ad10fd7e`
- Review target / 已测试 Head：`9e78538c0dec08fa9fcace49e068b8bc9d4d5af1`
- Owner / Agent：Codex
- 目标边界：活动 `a158aa8:rtl/div.v`
- 远端：实现提交已推送；不自动创建、标记 ready 或合并 PR

## 选择理由

前置迭代已经锁定 9 端口和 E33/E34/E35/E36 历史逐拍行为。本轮直接用 SpinalHDL 替换活动 `rtl/div.v`，并把验证入口接到既有统一 Make target；不迁移无关模块、不做性能优化。分支 stacked 在未合并的 harness 分支上，因此只允许 Draft。

## 行为合同与实现

合同见 `docs/contracts/div.md`。新增 `OpenLa500Div` 和独立生成器，使用显式 `div_clk` ClockDomain 与同步高电平 `reset`。生成模块精确为 `div`，端口为 `div_clk/reset/div/div_signed/x/y/s/r/complete`，无隐式 `clk/resetn`。

历史时序被保留：E33 `complete=1` 时商已经是最终值、余数仍是历史值；E34 捕获最终余数且 `complete=0`；E35 cleanup；请求保持高时 E36 重新作为 E1。abort、late abort、operand change、除零与有符号溢出均进入固定差分轨迹。

生成 RTL 为 4747 bytes，SHA256 `0c022398490e29cb92cd7adc31d2e35b26e47c3ea5a4b84316a54cfbbae0f349`。Golden SHA256 为 `7e499f4c43c92154d1d4e21be2f269ac140b4f2b2d944677c71f6f4213b66dc6`。

## 修改文件

- `spinal/src/main/scala/openla500/execute/OpenLa500Div.scala`
- `spinal/src/main/scala/openla500/execute/GenerateOpenLa500Div.scala`
- `reference/component-replacements/div.v` 与 `div.json`
- `tools/div_gate.py`、`tools/div_diff.py` 与对应测试
- `Makefile` 中 `alu/mul/div` 的显式 target 分派
- 本迭代中文日志、状态和证据索引

## 尝试与失败

1. 先精确验证了 `complete` 脉冲与余数晚一拍捕获，没有用数学商余数掩盖历史可见时序。
2. 独立 gate 审查发现 formal 负控分类过宽、candidate provenance 不足和误导性的未用参数；在 `9e78538` 修复并重跑全部 commit-bound gate。未知 `TARGET` 另行实际执行并返回 2。
3. Verilator C++ 后端不能同时接受模块和端口都叫 `div`。Lint 只在私有快照中改唯一模块声明为 `div_lint`；port、Yosys、formal 与差分仍消费原始 committed RTL。
4. Vivado 首次结果含不适用约束，第二次漏加载约束，第三次因打开设计前创建时钟而返回 1；最终 `golden-final` 与 `candidate-final3` 均 batch rc=0。审计进一步发现 DRC、methodology 和 timing 未通过，因此严格 Vivado gate 保持 FAIL。
5. 首次 chiplab doctor 在 Windows/v9fs reference 和泄漏 `GIT_DIR` 下失败；改用只读 WSL-native `/opt/chiplab-reference` 与 clean ext filesystem source 后 doctor PASS，没有放宽 lock。
6. 官方 locked/mixed `func_lab19` 均实际运行并在同一既有 PC 失败。`identity-compare` 因 replacement bytes、RTL projection 和 warning count 不同正确返回 FAIL。
7. Claude job `a62471f...` 在模型启动前因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败；原始事件已保存，独立代理审查不冒充 Claude。

## Commit-bound 本地门禁

| Gate | 结果 | 摘要 |
|---|---|---|
| Windows + chiplab doctor | PASS | Vivado 2023.2、chiplab `a2e11b3`、myCPU `aa3bde1` 与工具哈希匹配 |
| Automation | PASS | 255/255，0 skip |
| Scala | PASS | format/compile/test-compile/test 4/4 |
| Contract / elaborate / generate | PASS | 9 端口；两次生成字节一致 |
| Verilator / Yosys | PASS | 0 warning；hierarchy/check PASS |
| Cycle differential | PASS | 40 directed + 4096 fixed-seed random，4136 transaction、145131 edge、0 mismatch |
| Oracle 负控 | PASS | 3/3 均制造并检出预期 mismatch |
| Protocol formal | PASS | 3/3；只证明 2-state pulse/order，不证明算术或 golden 等价 |
| Chiplab overlays | PASS | locked 0 replacement；mixed 只替换 committed `div.v` |
| Official func smoke | FAIL | 两侧均在 `0x1c07c79c` 失败，且 warning policy 失败 |
| Identity compare | FAIL | parser/trace/ROM/ELF 相同，但不是 byte/RTL/warning identity |
| Vivado leaf | FAIL | synthesis 完成；timing、DRC、methodology、warning 未通过 |
| Claude review | UNAVAILABLE | reviewer 模型未启动 |

## 官方 chiplab 诊断

两侧各执行 1 项、失败 1 项、skip 0。首错均为 `0x1c07c79c` 的 t0：expected `0x6e2`、actual `0x8`；均为 172552 instructions / 602903 clocks，trace SHA256 均为 `8efa7942...38acb`。Locked warning 为 644（DUT 280 + official 364），mixed 为 641（DUT 277 + official 364）。这只支持“单个已知失败 case 的选定观测没有更早分歧”，不支持功能或集成 PASS。

## Vivado 2023.2 叶子诊断

| 项目 | Golden | Candidate |
|---|---:|---:|
| LUT / FF | 290 / 107 | 245 / 107 |
| BRAM / DSP | 0 / 0 | 0 / 0 |
| WNS / TNS | -0.364 / -7.803 ns | -1.800 / -86.872 ns |
| failing endpoints | 41 / 376 | 62 / 375 |
| methodology | 132 XDCH-2 | 132 XDCH-2 + 57 TIMING-16 |

两侧 DRC 均有 NSTD-1、UCIO-1 Critical Warning 与 CFGBVS-1 Warning，主 log 各有一条 Synth 8-7080。约束是 10 ns clock 加人工 2 ns I/O delay，且没有 implementation/bitstream，不能据此声称 Fmax、整机资源或性能改善。

## Claim、风险与回退

当前只允许声明：锁定的合法 held-request 合同窗口内，固定 4136 个 transaction 逐拍一致；精确端口、静态 RTL和有限协议 formal 通过；standalone Vivado leaf synthesis 完成并记录资源。

不得声明完整顺序形式等价、所有 invalid window 等价、official func、整机集成、timing、性能、58/81、random multi-seed、U-Boot/Linux 或 FPGA 通过。Scala 仍不是整机活动逻辑唯一真源。

回退通过 revert 本迭代 PR，恢复 `rtl/div.v` 的 golden overlay；不删除 harness、reference 或证据。下一项直接进入 `CoreTopCompat` 的官方 49 端口合同与薄兼容壳，不继续横向堆叶子。
