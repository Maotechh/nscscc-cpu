# Claude 审核状态

状态：`open`（bridge 不可用）。调用返回 `Required provider environment variable is not set: GEEKPIE_CLAUDE_API_KEY`，因此没有 Claude reviewer 内容，不能把本地审核称为 Claude 审核。

本地独立只读审核确认：

- 已修复：Verilator warning 不再无条件视为通过，仅读取并校验允许的 warning ID。
- 已修复：fixed seed `20260713` 写入 gate summary。
- 已修复：flush pending 满状态的 golden 优先级差异。
- 保留开放项：单 seed、2048 周期 trace；idle/icacop/中断/复位重入覆盖不足；port parser 只证明 name/direction/width 集合。

结论：允许 claim 仅限隔离 IF candidate 的固定 seed trace differential pass；不得升级为整机、官方 chiplab 或完全重构完成。
