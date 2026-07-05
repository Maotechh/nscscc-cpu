# nscscc-cpu - 2026 龙芯杯 CPU 设计

## RTL 源文件（双源）
- **`spinal/`** — SpinalHDL 源码（主 RTL，推荐修改入口）
  - ~2000 行 Scala，15 个模块
  - cacop 修复已内嵌
  - `sbt compile` 即可编译
  - `sbt "runMain openla500.GenAll"` 生成 Verilog 到 `rtl/`
- **`rtl/`** — Verilog 文件（chiplab 构建使用）
  - 11 个模块由 Spinal 生成（含 cacop fix）
  - 6 个模块为手写 Verilog（IDStage/EXEStage/MEMStage/WBStage/BTB/AxiBridge）
  - 待 SpinalHDL 1.8.x 可用后，全部从 Spinal 生成

## 优化记录
- BTB 32→64 入口（分支预测提升 ~10%）
- Dual-issue RegFile（4读2写）
- Store Buffer 4-entry（减少写停顿）
- PLL 36MHz（频率提升 10%）
- cacop 修复（ICache/DCache FSM bypass）

## 使用
1. `cd spinal && sbt compile` 编译 Spinal
2. `sbt "runMain openla500.GenAll"` 生成 Verilog
3. 将 `rtl/*.v` 放入 chiplab `IP/myCPU/`
4. chiplab 标准流程构建位流

## GitHub
https://github.com/Maotechh/nscscc-cpu
