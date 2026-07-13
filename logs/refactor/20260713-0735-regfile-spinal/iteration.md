# 20260713-0735-regfile-spinal

- 状态：`implementation_in_review / awaiting first commit`
- 分支 / Base：`refactor/20260713-0735-regfile-spinal` / `f621c7a1e056b9f128b86efddbdd2598b3692ecc`
- Owner：pipeline / Codex

## 选择理由

`regfile.v` 被活动 `id_stage` 直接实例化，边界小、无外部依赖，可立即进入 mixed overlay，并为 typed DecodeStage 提供唯一 GPR 状态实现。未实例化的 `regfile_dual.v` 不迁移。

## 合同与实现

Golden 为 `a158aa8:rtl/regfile.v`。Spinal 实现保留 2R1W、组合读、上升沿写、地址零读优先和同周期 bypass；不添加 reset，也不静默禁止写物理 slot 0。Scala generator 将 Spinal 展平的 DiffTest Vec 确定性改写成 legacy unpacked array 端口，生成单文件 `regfile.v`，活动寄存器逻辑仍来自 Scala。

## 已知失败尝试

- 首轮直接仿真 DUT 时，SpinalSim 注入未使用默认 clock/reset，`-Wall` 正确失败；改为测试专用 heartbeat wrapper。
- 首轮 wrapper 使用单个 DiffTest impl，base 配置出现 32 个 missing pin；改成确定性单模块端口变换，不使用 waiver。
- 字段名替换按升序导致 `rf_o_1` 误匹配 `rf_o_10`；首轮 lint 语法失败，改为降序替换后 base/DiffTest lint 均为零 warning。
- Yosys 0.33 在 `DIFFTEST_EN` 打开时无法解析 golden 同样使用的 unpacked array module port；非 DiffTest 活动综合配置已执行 `hierarchy -check; proc; check -assert` 并通过，DiffTest wrapper 由 Verilator 与 golden lockstep 覆盖，不宣称其 Yosys PASS。
- 首轮完整 Scala gate 仅 `scalafmtCheckAll` 失败，编译和测试已通过；格式修正后重新执行全部四项通过。

## 当前证据

- Scala directed/random：3 tests PASS；1024 随机交易。
- Golden/candidate Verilator cycle lockstep：4096/4096 PASS，包含完整 32×32 状态比较。
- Verilator base/DiffTest `-Wall`：PASS。
- Yosys 非 DiffTest 活动综合配置：PASS；DiffTest unpacked-array 端口：工具解析限制，未通过。
- Locked full Scala gate：4/4 PASS，生成 RTL 两次字节一致。
- Windows doctor：PASS，实际探测 Vivado 2023.2；仓库 Python automation：304/304 PASS。

## 回退与风险

回退为 revert 本迭代 PR。活动 overlay 和官方 smoke 尚待首次提交后运行；在此之前状态不超过 `implementation_in_review`。本轮不做 regfile 性能优化，也不把 leaf 差分扩大成整机功能 claim。
