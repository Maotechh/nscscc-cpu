# AXI Bridge 行为合同

## 固定事实源

- Golden commit：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`
- Golden path：`rtl/axi_bridge.v`
- Git blob：`4219790c25c653da1a061c5f4c674e062201b8e9`
- SHA256：`07c30c8e5e99373ecb988b2a5cc03e4e8cb7b6e22af26b1b37171a808b144f9e`
- 大小：10106 bytes
- 端口 manifest：`reference/component-contracts/axi-bridge.json`

Golden 是待复测 candidate，不是体系结构规范。差分只证明固定输入轨迹下的周期一致。

## 时钟与复位

`clk` 上升沿触发，`reset` 是高有效同步复位。复位清空三个状态机以及 valid/ready/write buffer 的活动状态。与 golden 一样，地址和数据 payload 寄存器在第一次对应请求前没有复位合同，测试不得比较其无效窗口值。

## 读请求

- 空闲时 data read 优先于 instruction read。
- 同时请求时 `data_rd_rdy=1`、`inst_rd_rdy=0`，只锁存 data request。
- cache-line 类型 `3'b100` 转成 `size=3'b010,len=8'h03`；其他类型原样进入 size，len 为 0。
- AR valid/payload 从接受请求后的周期保持到 `arready` 上升沿。
- 任意写事务未完成时不接受读；唯一例外是在 `bvalid && bready` 的响应完成沿同时接受读。
- R channel 永不反压：完成同步复位后 `rready` 始终为 1。
- `rid[0]==0` 直通 instruction response，`rid[0]==1` 直通 data response。data 始终直通 `rdata`，valid/last 只按 ID 路由；`rresp` 不参与历史控制。

## 写请求

- 只有 data write 活动；instruction write 的所有输入均为兼容死端口，`inst_wr_rdy` 恒为 1。
- 空闲时 `data_wr_rdy=1`，接受请求后先保持 AW；只有 `awready` 后才拉高 W valid。
- scalar 写为一拍 W，`wlast=1`；cache-line 写按 `data[31:0]` 到 `data[127:96]` 依次四拍发送，所有拍保持请求的 `wstrb`，第四拍 `wlast=1`。
- 最后一拍 W 握手后拉高 `bready`，直到 B 握手；`bid/bresp` 不参与历史控制。
- `awid=wid=4'h1`，burst 为 INCR，其余 cache/prot/lock 固定为 0。
- `write_buffer_empty` 仅在写状态空闲且剩余拍数为 0 时为 1。

## 差分观察窗口

逐拍比较所有固定输出、ready/valid、ID、地址、len/size、写数据/strb/last 和 cache 返回信号。复位后尚未被有效请求赋值的 AR/AW/W payload 允许 unknown，不纳入比较；一旦对应 valid 首次拉高，payload 必须逐拍一致并在握手前稳定。

固定 directed 轨迹至少覆盖 reset、双读优先级、AR backpressure、写期间读阻塞、B 完成沿接读、scalar 写、四拍 line 写、W backpressure、R ID 路由、连续事务和死 instruction-write 端口。随机轨迹对 AR/AW/W/B/R 延迟施加固定 seed backpressure。

## 完成范围

本边界通过要求：exact 65-port、locked Scala 生成、Verilator/Yosys 静态检查、directed + 固定 seed 随机逐拍 differential。单模块 overlay 的 `func_lab19` 只用于判断是否比已知 baseline 更早分岔；不得据此声明整机、58/81、random DiffTest、性能、Linux 或 FPGA PASS。
