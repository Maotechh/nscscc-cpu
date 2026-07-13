# 独立只读审核

结论：有条件接受有限诊断性 claim，PR 必须保持 draft。

- clean source HEAD `8f18ff7b7a01fce0ab5b21f6a71680a3fb8540c3` 的 13 个 committed replacement 被 diagnostic overlay 接受，其中 difftest-profile ID SHA 为 `0148176c...853b`。
- `func_lab19` 实际执行 1 项、失败 1 项、skip 0；原生 build/simulation 返回 0 不改变严格 FAIL。
- 首错、instructions/clocks、trace SHA 和 size 与锁定 baseline 一致，仅说明该单一失败观测没有更早的可见差异。
- 246 条 DUT warning 与 373 条官方环境 warning 均未批准；rtl-static、58/81、random、perf、system、FPGA 未执行。
- Claude bridge 缺 key，本文件是降级独立审核，不是 Claude 审核。
