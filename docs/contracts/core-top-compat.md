# core_top 兼容边界合同

## 事实源

`a158aa8:rtl/mycpu_top.v` 和锁定 chiplab myCPU gitlink `aa3bde1:mycpu_top.v` 的文件主体并不相同，但 `module core_top` 表头逐字节规范化后完全一致，SHA256 为 `43c1c564...fc309`。合同的机器可读版本是 `reference/core-top.ports.json`。

顶层固定为 49 端口：17 个 input、32 个 output。`aclk` 上升沿；外部 `aresetn` 低有效。历史核心在 `aclk` 上升沿把 `~aresetn` 登记为内部同步高有效 reset；兼容壳保留该一拍路径，将捕获寄存器以 BOOT 值 1 初始化，并增加一个 BOOT 值为 0 的 `externalResetSeen` 状态。核心在外部 reset 至少被拉低一次前保持复位，避免 bitstream 配置与 JTAG 装载 DDR 之间提前执行；首次有效 reset 之后的拉低、释放周期仍沿用原同步语义。

## AXI 与 debug

接口是历史 AXI3/WID 风格，不直接暴露 stock Spinal `Axi4`。五个 channel 的名称、方向和宽度必须与 manifest 完全一致。特别是顶层 `arlen/awlen` 保持 8 bit；锁定 nscscc-team SoC 的内部线网只取 4 bit，这是官方集成历史差异，不在壳内偷偷改宽。

Debug 包含 `break_point/infor_flag/reg_num`、`ws_valid/rf_rdata` 和五个 `debug0_wb_*` 输出。即使锁定 SoC 没有连接 `debug0_wb_inst`，生成顶层仍必须保留它。兼容壳不解释 commit 语义；未来 DiffTest 只能通过独立 `CommitEvent` adapter 扩展，不能越层读取流水内部信号。

## 迁移状态

当前 `CoreTopCompat` 已实例化 `SpinalCoreBackend`，完整生成 RTL 不再定义或实例化
`openla500_legacy_core`。完整 package 是单一生成文件，内嵌 typed 流水、CSR/TLB、Cache、
AXI bridge、mul/div 等 Spinal 组件；overlay 只能替换 `rtl/mycpu_top.v`，不得同时 overlay
旧叶子 replacement 造成重复模块定义。

这一结构事实只证明活动手写真源已切换，不证明功能等价。官方 32-entry BTB、LACC、完整 DiffTest/
ArchState、perf 以及官方 func/random/system/FPGA 门禁仍须分别取得证据。

`TLBNUM` 历史默认值为 32。打包后的顶层保留该参数以兼容官方 source contract，但活动 Scala 后端在 elaboration 时固定为 32，Verilog 参数 override 不受支持且不会改变硬件结构；Scala API 明确拒绝其他值。打包器把顶层 reset capture 约束为 `(!aresetn) || (TLBNUM != 32)`，因此任何非 32 override 都会让后端保持复位并 fail closed，而不会静默生成或运行错误配置；若唯一 reset capture 赋值不存在，打包直接失败。可配置的 immutable `CoreConfig` 和配置矩阵由后续整机 PR 建立，不得把该兼容参数表述为运行时或 Verilog elaboration 可配置。

完整 package 不使用外部聚合 warning waiver，也不传递宽泛的 `-Wno-*`。单文件承载多个 Spinal 生成模块所需的 `DECLFILENAME` 注解逐模块开启并在对应 `endmodule` 后关闭；已锁定的 36 个未消费兼容字段只在 `(module, signal)` 清单指定的唯一声明前后局部开启/关闭 `UNUSEDSIGNAL`。声明缺失、重复或漂移都会使打包失败，注解不得扩大到整个文件或整个 warning 类别。锁定 Verilator 5.020 对当前完整 package 的严格 lint 结果为 0 warning、0 error、0 skip；`CORE_TOP_LINT_WAIVERS` 默认留空，只有调用方显式指定文件时才进入 waiver 审计流程。

## 强制检查

- 49 端口名称、顺序、方向、宽度精确一致。
- 生成定义名为 `core_top`，无 `_zz_*` 业务端口和额外 `clk/resetn`。
- 上电启动互锁必须初始化为“尚未观察到外部 reset”，且只有采样到 `aresetn=0` 后才允许后端释放。
- 结构化 Yosys netlist 证明除启动互锁的 `externalResetSeen`、一拍 reset capture 及其组合逻辑外，
  每个顶层端口与后端同名端口一一连接，兼容壳不再引入其他逻辑、寄存器、CDC 或接口周期。
- Verilator 对完整 package 严格执行并要求零 warning、零 error、零 skip；Yosys 对完整 package 进行结构检查。这些本地门禁不替代官方 chiplab 编译和上板验证。
- fresh package、提交的 `mycpu_top.v` 和累计 replacement spec 必须逐字节及 SHA256 一致。
- 打包 overlay 恰有一个 `core_top`，并且全文不存在 `openla500_legacy_core` 标记。
- 官方 locked/mixed smoke 都实际运行；已有 baseline 失败必须与壳引入的新失败分开报告。
