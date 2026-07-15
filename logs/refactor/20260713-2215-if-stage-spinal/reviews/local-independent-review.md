# 独立只读审核

## Blocking（已修复）

1. 原 gate 使用 `-Wno-fatal` 且只看 return code，会吞掉未批准 warning。现已在 `tools/if_stage_gate.py` 提取 warning ID，并对白名单外 warning 置失败。
2. 原 evidence 仅在 `/tmp`。现已将最终生成 `reference/component-replacements/if_stage.v`、replacement spec、命令摘要和 review 文件纳入分支。
3. golden 的 flush pending 满状态优先 `pfs_ready_go` 清空，Scala 原先先处理 `flushDelay`。现已按空/满状态机改写并重新通过 gate。

## Open

- lockstep 固定 seed 单 trace，不等价于所有输入；idle、icacop、interrupt、reset re-entry 尚未系统覆盖。
- testbench 调试输出引用生成层级名，生成器重命名会影响测试编译。
- port check 证明 name/direction/width 集合，不证明声明顺序和完整 clock/reset 语义。

## 结论

当前证据支持“锁定 golden 与 candidate 在 seed `20260713` 的 2048 周期隔离 trace 上一致，且负控可检出”；不支持活动 overlay、chiplab、58/81 功能、NEMU random、Vivado 或整机完全重构 claim。
