# openLA500 mul golden harness 合同

## 范围与来源

- Golden candidate：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/mul.v`。
- Golden blob SHA256：`251d2bba3e659c294c9a004bbb2b542435fcfa0b0c1582cc1a7a3edca765a4c0`，6045 bytes。
- 活动实例：同一提交的 `rtl/mycpu_top.v` 中唯一 `u_mul`。
- Golden harness 由前置迭代建立；candidate 生成入口固定为
  `openla500.execute.GenerateOpenLa500Mul`，生成物仍必须由全部门禁证明后才可 overlay。
- 现有 `spinal/src/main/scala/openla500/Multiplier.scala` 的 ready/valid、32-cycle 和 32-bit result 合同不兼容，不能作为 oracle。

## 精确端口

Golden 顶层模块名为 `mul`：

| 名称 | 方向 | 宽度 | 语义 |
|---|---|---:|---|
| `mul_clk` | input | 1 | 上升沿采样时钟 |
| `reset` | input | 1 | 高有效同步 hold，不是清零 reset |
| `mul_signed` | input | 1 | 1 为 signed x signed，0 为 unsigned x unsigned |
| `x` | input | 32 | 乘数 |
| `y` | input | 32 | 被乘数 |
| `result` | output | 64 | 最近一次有效采样的 64-bit 模乘积 |

不允许 valid/ready、额外隐式 clock/reset、截断的 32-bit result 或端口重命名。

## 时序与 reset

Golden 唯一状态更新为：

```verilog
always @(posedge mul_clk) begin
    if (~reset) begin
        // capture Booth partial products
    end
end
```

因此合同是：

1. `reset == 0` 的每个 `mul_clk` 上升沿采样 `x/y/mul_signed`，该沿后 `result` 对应该次采样。
2. 吞吐率是一拍一个输入，没有 request/response 握手。
3. `reset == 1` 时同步保持内部状态；输入变化不得改变已知 `result`。
4. `reset` 不是异步 reset，也不初始化状态。首次 `reset == 0` 上升沿前 `result` 未定义，oracle 禁止比较。
5. 采样后、下一上升沿前任意扰动输入，`result` 必须保持最近一次采样结果。

这里的“沿后可见”称为相对输入采样的 1-stage/1-edge latency；测试报告必须给出具体 edge 对齐，不能只写“1 cycle”而不说明比较时刻。

## 数学语义

- unsigned：`uint64(x) * uint64(y)`。
- signed：`int64(int32(x)) * int64(int32(y))`，结果按 64-bit two's-complement bit pattern 比较。
- directed vectors 至少覆盖 0、1、`0xffffffff`、`0x80000000`、`0x7fffffff`、正负混合和 signed/unsigned 同位型差异。
- random 使用记录的固定 seed；向量数为正且不低于 4096。

## Harness 完整性

- contract JSON 未知字段、重复 key、非法 direction/width、path traversal、非锁定 commit/path/hash 均失败。
- Verilator、manifest、golden blob 和 driver 均记录 SHA256。
- Golden `rtl/mul.v:195` 的 `WIDTHEXPAND` 只能在
  `lint-waivers.yml` 精确匹配 commit、source SHA、行号和 scope 后抑制；
  该 waiver 不适用于任何 candidate。
- runner 先做一次有效采样，再检查 reset hold；不能利用 Verilator 2-state 初值把 golden 未定义状态当作 0。
- runner 必须检查 active edge 后结果、无时钟输入扰动 hold、连续每拍采样和 reset hold。
- warning、timeout、非零退出、零向量、首个 mismatch、缺 artifact 或 `SKIP` 都返回非零。
- golden self-check 只证明 harness 能执行并与独立数学模型一致；candidate 必须另跑相同向量和时序检查。

在 Windows + WSL 的 `/mnt/<drive>` 挂载目录中，GNU make 可能因宿主与 WSL
文件时间精度产生 `clock skew detected`。该 warning 也属于未批准 warning，runner
必须失败关闭；正式运行应把 `OUT_DIR` 指向 WSL 原生 `/tmp`（例如
`OUT_DIR=/tmp/nscscc-mul-make-unit`），并在迭代日志中保留 locator 和 SHA256。

## 后续 candidate 要求

本 `mul-spinal` 迭代必须提供精确端口、显式 `mul_clk` ClockDomain、同步 hold、cycle differential 和 first-capture-aware 顺序 formal。当前 formal 证明 candidate 在 2-state 语义下满足独立数学模型的 active capture 与 reset hold 合同，并不构成 candidate 与 golden Booth/Wallace 实现的形式等价证明。只有 candidate 实际进入 mixed overlay 后才能讨论 whole-CPU 可见回退；leaf PASS 不等于 `integrated_pass`。
