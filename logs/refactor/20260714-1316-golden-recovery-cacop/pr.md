# Draft PR：恢复 CACOP 局部行为并暴露下一处 branch replay 首错

- Iteration：`20260714-1316-golden-recovery-cacop`
- Branch：`refactor/20260714-1316-golden-recovery-cacop`
- Base / review target：`13e0c8da423bb75ca848aada91c67738f22a60ab` / `b2a73c83f9d849c6f67828e8dcfdd39a620e00ed`
- 状态：Draft / blocked；不自动创建、标记 ready 或合并

## 行为合同与修改

本 PR 只恢复 I/D Cache 的 CACOP 局部行为，并修复生成 RTL 内嵌 Git HEAD 导致的不可复现发布。定向 gate 对记录的两个候选 RTL SHA 在 958 拍轨迹上与 d22 局部 oracle 零 mismatch，并捕获 d76/2ff/408 三组负控；该 gate 未记录 source HEAD，不能直接绑定为整机 `b2a73c8` 等价证据。

## 验证

- Scala 4/4、generate/package/publish 3/3、49 端口和 Yosys：PASS。
- strict lint：FAIL；最终摘要未保留精确 warning 计数。
- 官方 `func_lab19`：`1/1/0/1/0`，越过旧 `0x1c07c79c`，仍 FAIL 于 `0x1c07cfcc`。
- 58/81、random、perf20、U-Boot、Linux、Vivado release gates：未执行。
- Claude bridge：已调用但缺少 `GEEKPIE_CLAUDE_API_KEY`，审核不可用。

## 风险与回退

本 PR 不支持完整 cache 等价、官方功能通过或完全重构 claim。回退方式是 revert 本 PR；下一 stacked 分支应先建立 branch/predictor replay harness，再处理重复提交。
