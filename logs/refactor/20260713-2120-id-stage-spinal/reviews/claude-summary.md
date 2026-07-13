# 独立审核降级记录

Claude bridge 因 `GEEKPIE_CLAUDE_API_KEY` 未设置而失败，不能称为 Claude 审核通过。本次仅记录执行代理的只读审查结论，PR 必须保持待评审状态。

- `accepted`: 四配置 generation 2/2、8259 周期差分、四配置负控、Scala gate；证据文件存在且摘要数字一致。
- `accepted`: 首轮 cycle 4 的非分支 BTB target 偏差已修复，并在修复后重新运行四配置差分。
- `open`: active `core_top` 集成、官方 58/81、NEMU random、perf、Linux 和 Vivado 尚未执行。
- `open`: Yosys 0.33 对 DiffTest unpacked-array 端口不兼容；仅 flattened projection 通过，不能升级为原端口直接 Yosys 通过。
- `open`: 尚未证明与 IF/EX/MEM/WB 组合后的精确异常和跨阶段时序。

结论：本地证据支持“ID stage 四配置局部差分通过”，不支持“整机或完全重构通过”。
