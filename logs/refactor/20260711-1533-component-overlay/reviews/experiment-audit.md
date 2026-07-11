# 实验完整性审计

- 日期：2026-07-12
- 审计对象：source HEAD `71a1995b7ca4dd922d1896e6b820e8029ff88575`
- 审计者：独立只读 Codex 子代理（不是 Claude）
- 总体结论：`WARN`

## A. Oracle 来源：PASS

locked 与 mixed 都使用锁定 chiplab `a2e11b3`、NEMU 和 `a158aa8` 文件清单。mixed 仅把 `rtl/alu.v` 替换为与 base SHA256 相同的已提交 blob。identity comparator 重新读取 Git blob、doctor、manifest、物理 artifact/raw log 和 publication marker，不从 DUT 输出生成“正确答案”。

## B. 分数归一化：PASS

本迭代没有性能分数或归一化指标。报告使用原始 instructions、cycles、warning counts 和 DiffTest mismatch，不做基于自身输出的归一化。

## C. 结果存在性：PASS

独立复算两侧 24 个 raw/artifact locator 的 SHA256 和 18 个 artifact size，均与报告一致；report/marker/script 哈希链匹配。关键 locator 与哈希见 `../artifacts.json`。两侧均为 `executed=1 / failed=1 / skipped=0`，首错和计数一致。

## D. 死代码/未执行入口：WARN

独立 `rtl-static`/Yosys 入口未执行。Windows 自动化含 8 个条件 skip，故不得晋升为正式 automation gate PASS。性能、Linux、FPGA 未执行。

## E. 范围：WARN

只有一个 `func/func_lab19` 用例，且 locked 与 mixed 都失败。该范围只能支持“等字节 replacement 的输入投影与选定失败观测一致”，不能支持 CPU 正确、RTL 等价、Spinal ALU 集成或功能 gate PASS。

## F. 评估类型

`simulation_only`：官方 Verilator + NEMU DiffTest 单用例诊断；不是 FPGA、Linux 或完整功能回归。

## Claim 影响

- C1：`supported_with_narrow_scope`。必须同时写明单用例、等字节 replacement、两侧失败和 `gate_eligible=false`。
- C2：`needs_qualifier`。自动化测试数字可记录为开发证据，但 Windows 有 8 skip，不能称正式 gate PASS。
- CPU/RTL 等价、完整 Spinal 重构、性能/Linux/FPGA PASS：`unsupported`。
