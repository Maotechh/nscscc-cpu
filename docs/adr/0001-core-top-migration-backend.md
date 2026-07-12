# ADR 0001：core_top 迁移后端

- 状态：Accepted for migration only
- 日期：2026-07-13

## 背景

锁定 chiplab 直接实例化 49 端口的 `core_top`。当前 Scala 的 `CPUCoreFlat` 和 `MyCPUTop` 都不满足该接口，也不能作为行为 golden。若在所有流水、特权和存储模块迁移完成后才建立顶层边界，各 owner 会继续依赖 Verilog 顶层内部信号，无法并行集成。

## 决策

建立零状态、零周期的 `CoreTopCompat`：它只拥有官方端口、显式 `aclk/aresetn` 时钟域声明和一一连接。内部后端合同保持与官方端口同构；后续可在不修改 SoC 的情况下切换为 typed Spinal core。

迁移期允许 generator 从锁定 Git object `a158aa8:rtl/mycpu_top.v` 机械地把唯一 `module core_top` 改名为 `openla500_legacy_core`，再与 Spinal wrapper 打包。机械变换必须校验原 blob、替换次数、剩余 bytes 和输出哈希。该文件不手工维护。

打包层保留 `#(parameter TLBNUM=32)`，并把参数传给 legacy backend。外部 `aclk/aresetn` 原样透传；不会把低有效 reset 直接改造成新的下游 reset 时序。

## 依赖方向

```text
locked chiplab ports
        |
        v
CoreTopCompat -> backend contract
                    |
          +---------+----------+
          |                    |
  legacy backend          OpenLa500Core
  (temporary)             (final target)
```

Compat 不得读取后端流水、cache、CSR 或 predictor 内部信号。完整 debug/DiffTest 以后只消费 `CommitEvent` 和显式架构状态。

## 后果与退出条件

优点是官方接口稳定，流水、特权、存储和观察 owner 可在同一 backend contract 后并行迁移。代价是中间态仍携带 legacy Verilog，状态最多为 `wrapped_golden`，不能计入纯 Spinal 完成度。

当 `OpenLa500Core(CoreConfig)` 通过所需整机 gate 后，删除 legacy 打包、改名工具路径和 BlackBox；`CoreTopCompat` 本身继续保留。若参数化顶层无法由最终 Spinal generator 直接表达，参数壳仍必须由同一可复现 generator 产生，不允许手工漂移。
