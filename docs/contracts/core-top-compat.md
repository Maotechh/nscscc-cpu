# core_top 兼容边界合同

## 事实源

`a158aa8:rtl/mycpu_top.v` 和锁定 chiplab myCPU gitlink `aa3bde1:mycpu_top.v` 的文件主体并不相同，但 `module core_top` 表头逐字节规范化后完全一致，SHA256 为 `43c1c564...fc309`。合同的机器可读版本是 `reference/core-top.ports.json`。

顶层固定为 49 端口：17 个 input、32 个 output。`aclk` 上升沿；外部 `aresetn` 低有效。历史核心在 `aclk` 上升沿把 `~aresetn` 登记为内部同步高有效 reset；兼容壳只透传外部时钟/reset，不新增寄存器、CDC 或周期。

## AXI 与 debug

接口是历史 AXI3/WID 风格，不直接暴露 stock Spinal `Axi4`。五个 channel 的名称、方向和宽度必须与 manifest 完全一致。特别是顶层 `arlen/awlen` 保持 8 bit；锁定 nscscc-team SoC 的内部线网只取 4 bit，这是官方集成历史差异，不在壳内偷偷改宽。

Debug 包含 `break_point/infor_flag/reg_num`、`ws_valid/rf_rdata` 和五个 `debug0_wb_*` 输出。即使锁定 SoC 没有连接 `debug0_wb_inst`，生成顶层仍必须保留它。兼容壳不解释 commit 语义；未来 DiffTest 只能通过独立 `CommitEvent` adapter 扩展，不能越层读取流水内部信号。

## 迁移状态

当前 `CoreTopCompat` 已实例化 `SpinalCoreBackend`，完整生成 RTL 不再定义或实例化
`openla500_legacy_core`。完整 package 是单一生成文件，内嵌 typed 流水、CSR/TLB、Cache、
AXI bridge、mul/div 等 Spinal 组件；overlay 只能替换 `rtl/mycpu_top.v`，不得同时 overlay
旧叶子 replacement 造成重复模块定义。

这一结构事实只证明活动手写真源已切换，不证明功能等价。64-entry BTB、LACC、完整 DiffTest/
ArchState、perf 以及官方 func/random/system/FPGA 门禁仍须分别取得证据。

`TLBNUM` 历史默认值为 32。打包后的顶层保留该参数并原样转发给兼容后端；本轮只验证默认值 32，Scala API 也暂时拒绝其他值。可配置的 immutable `CoreConfig` 和配置矩阵由后续整机 PR 建立，不据此声称统一配置已经完成。

## 强制检查

- 49 端口名称、顺序、方向、宽度精确一致。
- 生成定义名为 `core_top`，无 `_zz_*` 业务端口和额外 `clk/resetn`。
- 结构化 Yosys netlist 证明每个顶层端口与后端同名端口一一连接，且无额外逻辑/寄存器。
- Verilator/Yosys 对壳和审计 stub 零 error；这是 wrapper-only 结构检查，不替代官方 chiplab 对完整 package 的编译。
- fresh package、提交的 `mycpu_top.v` 和累计 replacement spec 必须逐字节及 SHA256 一致。
- 打包 overlay 恰有一个 `core_top`，并且全文不存在 `openla500_legacy_core` 标记。
- 官方 locked/mixed smoke 都实际运行；已有 baseline 失败必须与壳引入的新失败分开报告。
