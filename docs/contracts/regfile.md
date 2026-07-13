# 活动 RegFile 等价合同

Golden 为 `a158aa8:rtl/regfile.v`，blob `3caa2b688d0b6cd2e37b28d43ab5fad632e7d2f7`，原始 872 byte，SHA256 `e98d043d5166f8c2baf33692e74e3e2f203c8a80a3a2fae6b0f913ffb45d1203`。

- 两个组合读口、一个上升沿写口，无 reset。
- `we` 时写入包括物理 slot 0 在内的 `rf[waddr]`。
- 读地址 0 永远返回 0，优先级高于同周期 bypass。
- 非零读地址与有效写地址相同则立即返回 `wdata`。
- `DIFFTEST_EN` 变体暴露 32×32 原始物理数组；活动流水正常不写 x0，但模块合同不伪造该限制。
- 本轮只替换 `id_stage` 实际实例化的 `regfile.v`；未实例化的 `regfile_dual.v` 不在范围。
