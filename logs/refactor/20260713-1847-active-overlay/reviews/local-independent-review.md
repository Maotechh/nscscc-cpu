# 本地只读证据核对

1. 初版 reachability parser 对多 module 文件和条件编译的处理会扩大闭包；已改为 module block 隔离，并按 `DIFFTEST_EN=on/HAS_LACC=off` 预处理。负控确认 `lacc_core` 不能进入本 profile，`alu` 不能重复进入 aggregate spec。
2. strict overlay 的 `source_head`、spec hash、10 个 replacement blob 与 overlay manifest 一致；但报告明确 `gate_eligible=false`，只能支持 loader/provenance claim。
3. 原生 configure/build/simulation 均 exit 0，不等于 gate PASS。parser 显示功能 0/1，warning policy 显示 626 条未批准 warning，因此整项 `rtl-smoke` 必须是 FAIL。
4. 首错 PC 与旧 baseline 报告同为 `0x1c07c79c`，只支持“观察到同点首错”；没有逐 commit trace 比较，不能支持 sequential equivalence。
5. 未发现把 58/81、random、perf、Linux 或 Vivado 写成已通过的 claim；这些仍为未执行。

结论：claim A（10 个 committed replacement 同时被 strict loader 接受且完整层级可编译）有直接证据；claim B（单 case 同点首错）仅部分支持，必须保留非等价限定；claim C（不是完全重构）与源码/门禁现状一致。blocking issue 为官方功能失败、warning policy 失败及外部审核不可用。
