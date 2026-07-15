# openLA500 div golden harness 合同

## 范围与固定来源

- Golden candidate：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/div.v`。
- Golden Git blob：SHA-1 `225827c7d69addd280cb671c17e067a406a9171f`；原始内容 SHA256
  `7e499f4c43c92154d1d4e21be2f269ac140b4f2b2d944677c71f6f4213b66dc6`，2642 bytes。
- 活动实例：同一提交的 `rtl/mycpu_top.v` 中唯一 `u_div`。`exe_stage` 在除法期间保持
  `es_div_enable` 为高，直到 `div_complete` 解除流水停顿。
- 后续 SpinalHDL 生成入口固定为 `openla500.execute.GenerateOpenLa500Div`。生成物只有通过
  精确端口、逐周期差分、formal 和 mixed overlay 后才可替换活动 RTL。
- 现有 `spinal/src/main/scala/openla500/Divider.scala` 使用另一套 valid/result 接口，不是本合同
  的 oracle，也不能据其现状修改 golden 合同。

## 精确端口

Golden 顶层模块名为 `div`，且只能有以下九个端口：

| 名称 | 方向 | 宽度 | 语义 |
|---|---|---:|---|
| `div_clk` | input | 1 | 唯一采样时钟，上升沿更新状态 |
| `reset` | input | 1 | 高有效同步清零并回到 idle |
| `div` | input | 1 | 高电平 level request，事务中必须持续为高 |
| `div_signed` | input | 1 | 1 为有符号，0 为无符号 |
| `x` | input | 32 | 被除数 |
| `y` | input | 32 | 除数 |
| `s` | output | 32 | 商，在完成脉冲后的结果捕获沿后有效 |
| `r` | output | 32 | 余数，在完成脉冲后的结果捕获沿后有效 |
| `complete` | output | 1 | 高有效、单拍完成脉冲 |

不得把 `div` 改成单拍 valid，不得增加 ready/busy、隐式 clock/reset 或重命名端口。

## 逐周期 level 协议

以 reset 后或一次有效低电平 rearm 后，首个 `reset == 0 && div == 1` 的 `div_clk` 上升沿为
**接受沿 E1**。合同按沿后稳定值比较：

1. `x`、`y` 和 `div_signed` 从 E1 前建立，直到 E34 结果捕获沿后都必须保持稳定。
2. `div` 必须在 E1 至 E34 的 34 个连续上升沿均为 1。
3. E1 至 E32 沿后 `complete == 0`；E33 沿后 `complete == 1`，但此时只有商的迭代
   已结束，余数输出仍是旧值，**禁止把 `complete` 电平直接当作 `s/r` 同拍 valid**。
4. E34 是完成脉冲后的第一个上升沿。该沿锁存最终余数，沿后 `complete == 0`，`s/r`
   才共同有效，并保证稳定到 E35。完成脉冲因此仍恰好一拍。
5. 若 E34 结果捕获沿前任一上升沿看到 `div == 0`，该沿同步 abort 并 rearm；此前部分结果无效。
   保持低电平至少一个完整上升沿后，下一个高电平沿可以作为新事务 E1。
6. 若完成后一直保持 `div == 1`，E34 捕获结果，E35 完成 cleanup/rearm，E36 才是下一事务
   E1。也就是从 E33 完成通知起有两个后续沿，再在第三个沿启动。正常 producer 应在 E34
   捕获后使用一拍低电平明确分隔事务。
7. `reset == 1` 只在上升沿生效：该沿清零迭代状态、商、余数和符号缓存，回到 idle，
   `complete == 0`。reset 在时钟沿之间改变不得被当成异步 reset。
8. `s/r` 只在 E34 沿后到 E35 沿前的一个周期共同有效，此时 `complete == 0`。其他时刻
   可能是中间值或历史值，oracle 禁止比较。特别是 abort 不产生有效结果，也不能利用
   Verilator 的 2-state 初值把未完成输出视为定义值。

源码注释“执行需要 34 个周期”包含指令进入 EX 级、`es_div_enable` 尚未拉高的那个流水沿。
对独立 `div` 端口，从 E1 到完成脉冲是精确的 33 个请求高电平沿，最终 `s/r` 在 E34
结果捕获沿后有效；CPU 的 MEM 级在这个 E34 后的周期消费结果。三者不得混淆。

## 算术语义

- `y != 0`、unsigned：`s = uint32(x) / uint32(y)`，`r = uint32(x) % uint32(y)`。
- `y != 0`、signed：按 32-bit two's-complement 解释输入，商向零截断；余数绝对值小于除数，
  非零余数符号与被除数相同。输出按 32-bit two's-complement bit pattern 比较。
- `0x80000000 / 0xffffffff` 的 signed overflow 按 32 bit 回绕：商 `0x80000000`，余数 0。
- 除零必须保留 golden 的实际行为，而不是用宿主语言异常或另一个 ISA 约定代替：
  - unsigned：`s = 0xffffffff`，`r = x`；
  - signed 且 `x[31] == 0`：`s = 0xffffffff`，`r = x`；
  - signed 且 `x[31] == 1`：`s = 0x00000001`，`r = x`。

## Harness 完整性

- contract JSON 的未知字段、重复 key、路径穿越、端口增删/改宽、协议周期变化、非锁定
  commit key/path/hash/size 均必须 fail closed。
- validator 必须从 `reference/manifest.lock` 解析完整 40-hex golden commit，确认 `rtl/div.v`
  位于 `reference/golden-rtl-files.lock`，并用 Git plumbing 读取 `blob`；不得读取工作树同名文件。
- Windows worktree 的 `.git` 指针在 WSL 中必须解析到 `/mnt/<drive>/...` 或
  `/cygdrive/<drive>/...`；元数据缺失、对象类型异常或 Git 命令失败均为失败。
- runner 至少覆盖 directed 边界、4096 个固定 seed 随机事务、E33 complete 对齐、E34 结果
  捕获、单拍脉冲、中途 abort、一拍低 rearm、持续高电平 cleanup、同步 reset 和输入稳定约束。
- warning、timeout、非零退出、零事务、首个 mismatch、缺 artifact 或 `SKIP` 均使 gate 非零。
- leaf harness PASS 只证明该模块合同，不代表流水线、DiffTest 或 whole-CPU integrated PASS。
