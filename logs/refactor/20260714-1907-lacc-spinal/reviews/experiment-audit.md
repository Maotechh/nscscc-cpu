# LACC 实验与 Claim 完整性审计

- 审计对象：`7364f89ab5caa4e95234fa938022bc356092e54e`
- 审计者：独立只读 Codex 子代理，非 Claude/GPT-5.4
- 总体结论：`WARN`
- 完整性结论：未发现 phantom result、候选自比较、伪造 golden 或指标归一化；窄范围 claim 有证据支持，但评估范围不足以提升为整机集成或 ready PR。

## A. Golden provenance：PASS

- golden candidate 固定为 `a158aa8...`；`tools/lacc_diff.py` 用 `git cat-file` 读取两个独立 RTL blob，并强制校验 SHA256。
- golden/candidate 是两个不同模块，未发现把 candidate 复制为 golden 的自比较。
- a158 仍明确标记为 candidate；其 `func_lab19` baseline 在 `0x1c07c79c` 失败，没有被包装为 golden truth。

## B. Score normalization：PASS

- 比较器逐周期比较 valid、有效 payload、memory transaction 和 backpressure 稳定性，不计算归一化分数。
- negative control 反转 candidate response-valid，实际触发 mismatch，证明比较器能失败。

## C. Result existence：WARN

- `commit-bound-gates.json` 引用的 15 个 summary 全部存在且 SHA256 匹配。
- Scala、leaf/top 生成 summary 直接记录 `repo_head_sha=7364f89...`；unit/contract 本身不嵌 HEAD，但 candidate RTL SHA 与提交绑定生成物一致，形成间接 hash 链。
- 官方 smoke 的 6 个汇总 artifact、3 个原生命令日志和 raw report 中 9 个 build/trace artifact 均存在且 hash 匹配。
- 当前 trace 实测 174069 行，SHA256 `80420ff3...09d8`；与 `eadf441` raw trace hash、parser JSON 完全相同。
- whole-top lint 日志实测 off 80、on 81，与汇总一致。
- WARN 原因：本审核发生在证据 follow-up commit 前；实现已固定为 `7364f89`，但本审核文件和最终 evidence index 尚待提交。

## D. Dead metric / execution：PASS，附语义限制

- `run_candidate` 由 Makefile 实际调用；compile、positive、negative-control 均有退出码和耗时。
- coverage 字段参与 pass marker 和非零检查，不是死指标。
- `requests=145` 是 request-valid 周期数，`data=56` 是 memory-valid 周期数，不是唯一 transaction 数；只有 reads/writes 按 ready handshake 计数。
- negative control 只注入 response-valid 故障，不证明 address/write-data 等每条 comparator 分支都做了 fault injection。

## E. Scope：WARN

实际范围仅包含固定 seed `0x158aa8`、8192 周期、Verilator two-state、合法有序 response、一个 LACC+DCache 定向场景和一个默认 LACC-off `func_lab19` diagnostic。未覆盖四态、formal、多 seed、LACC-on 官方 workload、58/81、random、perf、system 或 FPGA。

## F. Evaluation type

- LACC leaf：`simulation_only`，相对锁定历史 RTL candidate 的 differential。
- LACC+DCache：`simulation_only`，单个 directed integration scenario。
- 官方 smoke：`simulation_only`，锁定 chiplab/NEMU mixed-candidate diagnostic；`gate_eligible=false`。

## Claim disposition

- `lacc_two_state_cycle_diff`：`qualified / supported`。
- `lacc_dcache_directed`：`qualified / supported`。
- `dual_config_elaboration_yosys`：`accepted with disclosure`，必须同时披露 strict lint 80/81 FAIL。
- `standalone_candidate_lint_clean`：`qualified / supported`，只限 leaf candidate。
- `default_lacc_off_trace_unchanged`：`qualified / supported`，只限与 `eadf441` 的单例 trace/parser 相同。
- `official_func_lab19_pass`：`rejected`，parser 到 test end 不覆盖 `good_trap=false`、608 条 warning 和总 gate FAIL。
- LACC-on 官方集成、四态等价、完整重构、release-ready、Vivado/FPGA：`unsupported`。

本审核允许 LACC 叶子维持 `differential_pass`，不允许提升为 `integrated_pass` 或 ready PR。
