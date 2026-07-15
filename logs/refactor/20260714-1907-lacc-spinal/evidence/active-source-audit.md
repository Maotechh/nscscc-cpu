# 活动源码完整性审计

独立只读代理逐项对照 `a158aa8:rtl/mycpu_top.v` 的活动实例与当前 `SpinalCoreBackend`、归档生成 RTL。

## 结论

- 当前工作树源码映射层面，IF/ID/EX/MEM/WB、ALU、mul/div、CSR、TLB/地址转换、I/D Cache、AXI、BTB、LACC-on/off 和 DiffTest adapter 均有活动 Scala 路径。
- 唯一仍未接入 active backend 的 a158 状态模块是 `perf_counter`。`PerfCounter.scala` 已存在，`WritebackStage` 也产生七类事件，但 backend 尚未实例化/连接。
- `ChiplabDiffTestBlackBox` 只是官方仿真 DPI sink；字段适配、commit counter 和架构状态连接在 Scala 中完成，不是旧 CPU Verilog 实现依赖。
- 默认 LACC-off 归档 generated RTL 不实例化旧 `lacc_core`；LACC-on 目前只在本轮源码和临时生成物中验证。

## 证据

- Golden 顶层实例：IF 373、ID 435、EXE 507、div 578、mul 590、条件 LACC 599、MEM 627、WB 694、CSR 776、AXI 876、AddrTrans 952、I$ 1013、D$ 1052、BTB 1092、PerfCounter 1117、条件 DiffTest 1129。
- Backend：stage 83-92；CSR/AddrTrans/cache/AXI/div/mul 94-100；predictor 170；DiffTest 337；LACC 389（本轮行号，提交格式化后可能平移）。
- `WritebackStage.scala` 产生 retired/branch/I$ miss/D$ miss/memory/predicted/error 七类 perf event；生成 RTL此前仅有未消费的 perf wires。

因此本轮之后仍不能宣称“完全重构”。在接入 `perf_counter`、重新生成归档 RTL并通过官方/full/random/system/fpga gate之前，最强结论只是“活动 CPU模块均已有 Scala source path，尚有一个活动状态模块未接线”。
