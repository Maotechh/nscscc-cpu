# 活动分支预测器行为合同

## 范围

本合同替换 `SpinalCoreBackend` 内联的 32-entry direct-mapped always-taken 临时逻辑，建立活动
`openla500.predict.OpenLa500Predictor`。它只负责 BTB、return-site matcher 和运行时返回栈；
Fetch/Decode 流水策略仍由现有 stage 拥有。

## 接口与时序

- lookup request 使用 `Flow[PredictorLookupRequest]`，只在 `valid` 时锁存 PC。
- prediction 使用 `Flow[PredictorPrediction]`，对应上一拍有效 lookup；miss 时 `valid=false` 且
  `taken/target/legacyIndex` 全部为零。
- update 使用 `Flow[PredictorUpdate]`，只在 Decode 指令实际离开该级时生效。
- valid lookup 后，输入 PC 在无新 request 时变化不得产生新预测。
- predictor 与流水处于同一显式核心 ClockDomain，不引入 CDC。

## BTB

- 官方 32 项全相联 PC matcher，每项保存 word PC、word target、valid 和 2-bit 饱和计数器。
- counter `2/3` 预测 taken，`0/1` 预测 not-taken；新项从 `2` 开始。
- add 不复用同 PC 项，依次选择最低 invalid、最低 strongly-untaken、5-bit LFSR 项。
- target correction 和 counter update 使用官方 5-bit `operateIndex`，不按 PC 重新匹配。
- `delete_entry` 是官方端口中的保留输入，aa3 活动 RTL 不消费它；默认 profile 不启用历史增强。
- target correction 同时把 counter 恢复为 `2`；counter update 按实际方向饱和加减。

## 返回预测

- 16 项 return-site matcher 记录已观察到的 JIRL PC；invalid 优先，满时使用 LFSR 低 4 bit。
- 独立 8 深度运行时 return stack；BL push `pc+4`，JIRL pop。
- 满栈 push 和空栈 pop 不改变状态；同拍 push 比 pop 优先，保持 aa3 的活动优先级。
- return-site hit 且栈非空时，返回栈顶并强制 taken；return prediction 优先于普通 BTB hit。

## 官方兼容与 a158 诊断

Fetch payload 保留官方 5-bit `btbIndex`，并把它作为 target/counter 更新索引。返回 matcher 输出兼容的低 4-bit index。

`a158aa8:rtl/btb.v` 名义参数是 64/16，但存在 32-bit match/untaken vector、5-bit selector 和
6->5 bit index 截断。其 `32'b0` reset 赋值会零扩展，仍可清零 64-bit valid vector，不列为功能缺陷。
默认 profile 绑定官方 aa3 的 32-entry/2-bit/RAS 行为；a158 的 64-entry 改动只作为历史诊断，不能替代官方来源。

## 必测不变量

1. accepted lookup 一拍响应；invalid payload 清零；无 request 不产生预测。
2. 官方 32 项均可命中；target/counter 更新由 5-bit legacy index 选择。
3. counter 在 `0`/`3` 饱和，taken threshold 正确。
4. add/target correction/counter update 只修改 legacy index 或被选择的一项；默认 profile 不实现 delete。
5. replacement 优先 invalid，再 strongly-untaken，再 LFSR。
6. RAS push/pop/full/empty 和 return-site replacement 正确。
7. 集成后 `core_top` 端口、生成可复现性和官方 mixed diagnostic 不回退。
