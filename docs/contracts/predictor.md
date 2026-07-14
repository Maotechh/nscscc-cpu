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

- 64 项全相联 PC matcher，每项保存 word PC、word target、valid 和 2-bit 饱和计数器。
- counter `2/3` 预测 taken，`0/1` 预测 not-taken；新项从 `2` 开始。
- add 优先复用同 PC 项；否则依次选择最低 invalid、最低 strongly-untaken、6-bit LFSR 项。
- delete、target correction 和 counter update 均按完整 `operatePc` 重新匹配 64 项，不依赖旧
  5-bit `operateIndex`。
- target correction 同时把 counter 恢复为 `2`；counter update 按实际方向饱和加减。

## 返回预测

- 16 项 return-site matcher 记录已观察到的 JIRL PC；invalid 优先，满时使用 LFSR 低 4 bit。
- 独立 8 深度运行时 return stack；BL push `pc+4`，JIRL pop。
- 满栈 push 和空栈 pop 不改变状态；同拍 push 比 pop 优先，保持 a158 的活动优先级。
- return-site hit 且栈非空时，返回栈顶并强制 taken；return prediction 优先于普通 BTB hit。

## Legacy 兼容与 a158 修正

Fetch payload 保留历史 5-bit `btbIndex`，只输出内部 6-bit BTB entry 的低 5 bit；该字段不得再
决定更新目标。返回 matcher 输出兼容的低 4-bit index。

`a158aa8:rtl/btb.v` 名义参数是 64/16，但存在 32-bit match/untaken vector、5-bit selector、
32-bit reset literal和 6->5 bit index 截断。本实现遵循其可辨识的 64-entry/2-bit/RAS 意图，
不复刻这些宽度 bug。`delete_entry` 在 a158 中未消费，但临时活动 backend 已实现删除；本实现
保留该可见修复，防止非分支 PC 留下幽灵预测。

## 必测不变量

1. accepted lookup 一拍响应；invalid payload 清零；无 request 不产生预测。
2. 64 项上下半区均可命中，低 5-bit index 冲突不影响 PC 精确更新。
3. counter 在 `0`/`3` 饱和，taken threshold 正确。
4. add/delete/target correction 只修改匹配或被选择的一项。
5. replacement 优先 invalid，再 strongly-untaken，再 LFSR。
6. RAS push/pop/full/empty 和 return-site replacement 正确。
7. 集成后 `core_top` 端口、生成可复现性和官方 mixed diagnostic 不回退。
