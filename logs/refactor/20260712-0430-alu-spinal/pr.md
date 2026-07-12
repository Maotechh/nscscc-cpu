# Draft PR：以 SpinalHDL 等价替换活动 ALU

## 状态

`awaiting_push`。这是基于 `refactor/20260711-1533-component-overlay` 的 stacked Draft；当前不自动创建 PR、不标记 ready、不合并。

## 行为合同

用 Scala 手写真源生成精确兼容 `a158aa8:rtl/alu.v` 的组合 `alu`：14-bit masked-OR、zero/multi-hot、ANDN/ORN、四个固定端口、无 clock/reset。

## 验证

- doctor 与 chiplab-doctor：PASS。
- Scala：4/4 PASS。
- 两次隔离生成：可复现，提交 RTL SHA256 `1349173904c772225ed4184a7e65aa88f7278fbcd060d33d81c966954c128146`。
- port / Verilator lint / Yosys static：PASS；模块 lint 0 warning。
- unit：3/3，4096 fixed-seed vectors。
- formal：Yosys 2-state 组合等价，78 个输入变量。
- 官方 `func_lab19`：candidate 与 mixed 都执行并 FAIL；两侧 172552 instructions、602903 cycles、同一首错与同一 trace SHA。mixed warning 642，比 candidate 少 2，但 warning policy 仍 FAIL。
- Claude review：unavailable；因此只能保持 Draft 和 `implementation_in_review`。

## 影响

不修改 decode、pipeline、cache、CSR、mul/div 或外部协议。本轮不做性能优化；未执行 perf、Linux 或 FPGA job，不声明 Fmax/LUT/FF/BRAM。

## 风险

- Whole-CPU baseline 本身在 `func_lab19` 失败，无法给出 integrated PASS。
- Yosys 证据是 2-state 组合等价，不覆盖 X/Z 传播或物理实现。
- 642 条 whole-CPU Verilator warning 尚无逐条 waiver。
- Claude required review 未完成。

## 回退

revert 本 Draft PR；`a158aa8:rtl/alu.v` 继续作为 oracle 和参赛稳定实现。
