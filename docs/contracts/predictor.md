# 活动分支预测器行为合同

## 范围

本合同替换 `SpinalCoreBackend` 内联的 32-entry direct-mapped always-taken 临时逻辑，建立活动
`openla500.predict.OpenLa500Predictor`。它只负责 BTB、return-site matcher 和运行时返回栈；
Fetch/Decode 流水策略仍由现有 stage 拥有。

## 接口与时序

- lookup request 使用 `Flow[PredictorLookupRequest]`，只在 `valid` 时锁存 PC。
- prediction 使用 `Flow[PredictorPrediction]`，对应上一拍有效 lookup；miss 时 `valid=false` 且
  `taken/target/legacyIndex` 全部为零。
- update 使用 `Flow[PredictorUpdate]`；普通分支在 Decode 实际离开该级时生效，延迟分支在 EX
  实际离开该级时生效。
- valid lookup 后，输入 PC 在无新 request 时变化不得产生新预测。
- predictor 与流水处于同一显式核心 ClockDomain，不引入 CDC。
- prediction 同时携带预测时的 `phtIndex/baseTaken/localTaken`；Fetch、Decode 和 EX 必须原样
  保存这些元数据，训练时不得用更新时的 PC 或历史重新计算。

## BTB

- 官方 32 项全相联 PC matcher，每项保存 word PC、word target、valid 和 2-bit 饱和计数器。
- counter `2/3` 预测 taken，`0/1` 预测 not-taken；新项从 `2` 开始。
- add 不复用同 PC 项，依次选择最低 invalid、最低 strongly-untaken、5-bit LFSR 项。
- target correction 和 counter update 使用官方 5-bit `operateIndex`，不按 PC 重新匹配。
- `delete_entry` 是官方端口中的保留输入，aa3 活动 RTL 不消费它。
- target correction 同时把 counter 恢复为 `2`；counter update 按实际方向饱和加减。

## 方向预测

- 活动 `SpinalCoreBackend` 启用局部历史 tournament；预测器叶级构造器默认关闭该功能，以保持
  legacy 叶级生成和独立基础行为测试兼容。
- 每个 32-entry BTB 项保存独立 8-bit 局部历史；共享 PHT 有 256 个 2-bit 饱和计数器，复位值
  为 weakly-taken `2`。
- PHT 索引为预测时 `localHistory(entry) XOR pc[9:2]`；PHT counter 的 MSB 是局部方向结果。
- 每个 BTB 项有独立 2-bit chooser，复位/新建项值为 `1`；chooser MSB 为 `1` 时选择局部预测，
  否则选择原 BTB counter。返回预测仍拥有最高优先级。
- 新建 BTB 项时局部历史初始化为该分支的实际方向。已命中方向更新使用预测时携带的 PHT
  索引训练 PHT，并把实际方向移入对应 BTB 项的 8-bit 历史。
- 仅当 base/local 预测不同才训练 chooser：局部预测正确时饱和增加，base 预测正确时饱和减少。
  add 和 return-pop 不训练方向表；target correction 可与一次合法方向训练同拍完成。

## 返回预测

- 16 项 return-site matcher 记录已观察到的 JIRL PC；invalid 优先，满时使用 LFSR 低 4 bit。
- 独立 8 深度运行时 return stack；BL push `pc+4`，JIRL pop。
- 满栈 push 和空栈 pop 不改变状态；同拍 push 比 pop 优先，保持 aa3 的活动优先级。
- return-site hit 且栈非空时，返回栈顶并强制 taken；return prediction 优先于普通 BTB hit。

## 官方兼容与 a158 诊断

Fetch payload 保留官方 5-bit `btbIndex`，并把它作为 target/counter/history/chooser 更新索引；
同时保留预测时的 8-bit PHT 索引和两个分量预测。返回 matcher 输出兼容的低 4-bit index。

`a158aa8:rtl/btb.v` 名义参数是 64/16，但存在 32-bit match/untaken vector、5-bit selector 和
6->5 bit index 截断。其 `32'b0` reset 赋值会零扩展，仍可清零 64-bit valid vector，不列为功能缺陷。
默认 profile 绑定官方 aa3 的 32-entry/2-bit/RAS 行为；a158 的 64-entry 改动只作为历史诊断，不能替代官方来源。

## 必测不变量

1. accepted lookup 一拍响应；invalid payload 清零；无 request 不产生预测。
2. 官方 32 项均可命中；target/counter 更新由 5-bit legacy index 选择。
3. counter 在 `0`/`3` 饱和，taken threshold 正确。
4. add/target correction/counter update 只修改 legacy index 或被选择的一项；活动 profile 不实现 delete。
5. replacement 优先 invalid，再 strongly-untaken，再 LFSR。
6. RAS push/pop/full/empty 和 return-site replacement 正确。
7. 活动 profile 的局部历史、PHT、chooser 饱和训练及 prediction-time 元数据回传正确；叶级兼容
   profile 仍保持官方 base counter 行为。
8. 集成后 `core_top` 端口、生成可复现性和官方 mixed diagnostic 不回退。
