# BTB branch replay 行为合同

## 范围

本迭代只处理活动 `SpinalCoreBackend` 中临时 BTB lookup 的请求绑定，以及官方 `func_lab19` 首错附近的五条循环。完整 64-entry/2-bit/RAS BTB 迁移另行提交，不在本迭代宣称完成。

## Golden 约束

- d22/a158 `rtl/btb.v` 仅在 `fetch_en` 时锁存 `fetch_pc`。
- lookup 只使用上一拍真正接受的 fetch 请求：`fetch_en_r && fetch_pc_r == entry_pc && valid`。
- `fetch_en=0` 时改变输入 PC 不得产生新的预测事件。
- lookup 无效或未命中时，返回 target/index 必须为零，避免污染 IF 中按 golden 语义锁存并位或合并的预测结果。
- 每个接受的指令 token 最多产生一次 commit；flush/redirect 只能杀死更年轻 token。

## 最小 replay 程序

```text
1c07cfcc: st.w    $r15,$r12,0
1c07cfd0: lu12i.w $r16,2
1c07cfd4: add.w   $r12,$r12,$r16
1c07cfd8: addi.w  $r13,$r13,1
1c07cfdc: bne     $r13,$r14,1c07cfcc
```

首轮 branch miss 后建立预测项；后续每轮 commit PC 必须严格为 `cfcc,cfd0,cfd4,cfd8,cfdc`，不得重复 `cfdc`，不得在 fetch backpressure 时凭未接受 PC 产生预测。

## 通过条件

1. Scala 编译、单元测试、全配置 elaboration 通过。
2. 生成 RTL、端口、Yosys 和 strict lint 结果机器可读；warning 不得静默吞掉。
3. branch replay directed harness 或官方 smoke 能复现并定位首错；若官方 smoke 仍失败，只报告新首错。
4. 不得据此声称完整 BTB、58/81、random、perf、Linux、Vivado 或完全重构通过。
