# Draft PR: 迁移活动 EXE stage 到 SpinalHDL

状态：仅草稿；实现提交 `4c73068aad5a81b34181138b20184f894016f327` 已完成提交绑定验证，分支待推送；不创建或合并 PR。

## 范围

- 从 `a158aa8` 的 `rtl/exe_stage.v` 建立 typed `ExecuteStage`，并由显式同步 ClockDomain 的 `LegacyExecuteStage` 提供旧端口适配。
- 支持 `lacc_off` 与 `lacc_on` 两种生成配置；端口和宽度由 manifest 锁定。
- 提供可复现生成、profile 绑定端口检查、候选单独 Verilator lint、Yosys 检查、8192 周期 golden lockstep 和负控。
- 非 LACC replacement RTL 进入 `reference/component-replacements/exe_stage.v`；原 Verilog 仍可通过移除 replacement 回退。

## 证据

- 迭代目录：`logs/refactor/20260713-0729-exe-stage-spinal/`
- 仓库自动化：304/304；Scala gate：4/4。
- LACC off/on：生成 2/2、端口 1/1、候选 lint 0 warning、Yosys PASS、逐拍差分 8192/8192。
- 两个 profile 的负控均在 cycle 0 检出人为 `es_to_ms_valid` 反相。
- Windows doctor 19/19，Vivado 2023.2 ML Standard 版本与文件 hash 锁定。
- WSL chiplab doctor 全通过；mixed overlay 精确绑定提交和单个 EXE replacement。
- 官方 `func_lab19` mixed 与 locked baseline 的 trace SHA、172552 条指令、602903 周期和 `0x1c07c79c` 首错一致；两者都失败，不能计为功能 PASS。

## 不作出的声明

- 未声明 58/81 功能集、随机 DiffTest、性能、U-Boot、Linux、Vivado implementation/timing/bitstream 或整机重构完成。
- `lacc_flush` 的 golden 未驱动；当前只拥有 2-state 可观察一致证据，不等同四态等价。
- chiplab smoke 必须在干净提交和隔离 overlay 上运行；已知 baseline 在 `0x1c07c79c` 失败时只报告诊断结果。
- mixed 编译仍有 278 条 DUT 与 364 条官方环境未批准 warning；严格 warning gate 失败。

## 回退与评审

- 回退：revert 本迭代提交，或删除 replacement spec 中 EXE 条目。
- 合并由维护者决定；代理不自动创建、批准或合并 PR。
- 已三次尝试 Claude bridge，均在 reviewer 产出前失败；原始事件、独立只读 review 与 claim audit 分开记录，不将降级审核写成 Claude 结果。
