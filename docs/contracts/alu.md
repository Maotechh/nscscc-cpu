# openLA500 ALU 行为合同

## 范围与来源

- Golden candidate：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/alu.v`。
- 活动实例：同一提交的 `rtl/exe_stage.v` 中唯一 `alu` 实例。
- 本合同只迁移无状态组合 ALU，不修改 decode、pipeline、mul/div、cache、CSR 或性能结构。
- `a158aa8` 不是 whole-CPU golden truth；但该叶子模块可由锁定 RTL直接形成可执行组合等价 oracle。

## 精确端口

生成模块定义名必须为 `alu`，且只允许以下四个端口：

| 名称 | 方向 | 宽度 |
|---|---|---:|
| `alu_op` | input | 14 |
| `alu_src1` | input | 32 |
| `alu_src2` | input | 32 |
| `alu_result` | output | 32 |

不得出现 `io_` 前缀、隐式 `clk/reset`、额外 debug/overflow/cmp 端口或状态元素。

## 操作位与结果

`alu_op` 为 14-bit 位掩码，不仅是合法 one-hot enum：

| bit | 操作 |
|---:|---|
| 0 | ADD |
| 1 | SUB |
| 2 | SLT（有符号） |
| 3 | SLTU（无符号） |
| 4 | AND |
| 5 | NOR |
| 6 | OR |
| 7 | XOR |
| 8 | SLL |
| 9 | SRL |
| 10 | SRA |
| 11 | LUI/pass `alu_src2` |
| 12 | ANDN |
| 13 | ORN |

每个操作先独立计算 32-bit 结果，再由对应 op bit 扩展为 32-bit mask 后按位 OR。由此得到强制边界行为：

- `alu_op == 0` 时输出 0。
- multi-hot 时输出所有被选择操作结果的按位 OR；不得改成优先级 mux。
- ADD/SUB 为 32-bit 模运算，不对外输出 overflow。
- shift amount 只使用 `alu_src2[4:0]`。
- SRA 以 `alu_src1` 的 bit 31 做符号扩展。
- SLT/SLTU 结果只有 bit 0 可为 1。

## 生成合同

- Scala 是新 ALU 的手写真源；生成器异常必须非零退出，禁止 catch 后打印 `SKIP`。
- 生成只写显式 `OUT_DIR`，不得直接覆盖仓库 `rtl/`。
- 同一 source/tool lock 连续两次 clean generation 的 RTL SHA256 必须一致。
- 用于 chiplab replacement 的生成 RTL和 replacement spec 必须作为同一 source commit 中的普通 Git blob。

## 验证合同

1. Scala directed test：14 个操作、zero-hot、multi-hot、0/1/31 shift、符号/进位边界。
2. 固定 seed random test：以独立软件 oracle 比较生成组件输出，失败记录 seed/input/expected/actual。
3. Verilator `-Wall` lint；任何未批准 warning 失败。
4. Yosys hierarchy/proc/check；latch、未驱动和组合环失败。
5. Yosys 组合形式等价：golden RTL 与生成 RTL对全部 78 个输入位证明 `alu_result` 相同，使用 `equiv_status -assert`。
6. 端口 manifest 精确比较，额外 clock/reset 或端口失败。
7. mixed chiplab overlay/smoke 只作 whole-CPU 可见回退诊断。locked baseline 已知在 `func_lab19` 失败；到达相同 mismatch 不能算 func PASS 或 `integrated_pass`。

模块级全部通过后最多提升为 `differential_pass`。在 whole-CPU baseline、正式 func 和 claim review 未通过前，不得提升为 `integrated_pass`。
