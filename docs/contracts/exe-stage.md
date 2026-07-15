# EXE 级行为合同

## 固定事实源

- Golden：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/exe_stage.v`。
- Git blob：`e95171aba43330a3b0bf267d3bdd45162889cb3b`。
- SHA256：`cab20e05205c6bddff19f01fd15ad4cb671144debf0836982b45b334c686f526`，16242 byte。
- 非 LACC `DS_TO_ES_BUS_WD=350`，LACC 打开时为 353；`ES_TO_MS_BUS_WD=425`，forward bus 为 39。
- module/端口合同见 `reference/component-contracts/exe-stage.json`。

## 时序与握手

- `clk` 上升沿、同步高有效 `reset`；任一全局 flush 清除 `es_valid`。
- `es_allowin = !es_valid || (es_ready_go && ms_allowin)`；只在 `ds_to_es_valid && es_allowin` 时捕获 payload。
- `es_to_ds_valid` 报告槽位占用；`es_to_ms_valid` 报告本拍可向 MEM 发送。
- 除法请求为 level，`div_complete` 前保持 EXE；乘法只形成 decode forwarding hazard，乘除实际结果由历史 MEM 级选择。
- load/store、D-cache CACOP、PRELD 需要地址请求被接受；TLBSRCH 与 MEM 写 TLBEHI 冲突时停顿；I-cache CACOP 等待 `icache_unbusy`。

## 副作用与异常

- `excp_flush/ertn_flush/refetch_flush/icacop_flush/idle_flush` 以及 `ms_flush` 阻止新 memory side effect。
- 本级异常包含输入异常与地址非对齐异常；异常指令可以越过普通等待条件，但不得发出 data request。
- `data_valid`、CACOP/PRELD enable 只由有效、无异常、下游可接受且未 flush 的槽位产生。
- 精确保留历史 byte/half/word mask、store data replication、CSR mask、INVTLB、TLBSRCH、CACOP 与 PRELD 位级行为。

## LACC

- LACC-on 以同一 typed stage 的可选 contract 实现，exact wrapper 增加历史条件端口。
- 精确保留历史 `lacc_stall = es_lacc_req && !lacc_rsp_valid`、LACC data request 优先级和 legacy mask 计算。
- 历史 `lacc_flush` 未赋值；重构明确输出常量 0，以匹配 Verilator 2-state 观测。该结论不能外推为真实硬件上的四态等价，LACC 必须单独给出差分证据。

## 完成边界

本迭代只可声明 EXE 单模块合同、静态检查和已实际执行的差分结果。它不代表流水线、MEM、特权、整机 chiplab 或完全重构完成。
