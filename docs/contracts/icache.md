# I-cache 行为合同

## 固定事实源

- Golden commit：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`
- Golden path：`rtl/icache.v`
- Git blob：`39ec5931316a068b7e5e64169bd257f480db5640`
- SHA256：`85ba1acc69616dd8b19dae1578fc7e002c83fd435f90227f54068e4fa492675b`
- 大小：14887 bytes
- 端口 manifest：`reference/component-contracts/icache.json`

Golden 是待复测 candidate，不是体系结构规范。差分通过仅表示固定输入轨迹和 2-state 仿真窗口一致。

## 时钟、复位与 SRAM

`clk` 上升沿触发，`reset` 是高有效同步复位。状态机、请求缓冲、替换路、命中缓冲、读请求记录和 LFSR 有明确复位值；两路四 bank 数据 SRAM、两路 tag/valid SRAM 及其输出寄存器不复位。

SRAM 是单口同步读：`ena && !wea` 时在上升沿更新输出；写周期和 `ena=0` 时输出保持。数据 SRAM 支持 4-bit byte write mask，tag SRAM 整字写。生成 RTL 必须保持这些未初始化窗口，测试只在 reset 后通过可观测交易建立确定状态后比较。

## 请求、命中与流水接受

- `valid || icacop_op_en` 在 idle 接受；普通请求的 `addr_ok` 在 idle 恒为 1，在 lookup 命中时也为 1，从而支持逐周期命中。
- 普通 lookup 的 tag 和 `uncache_en` 直接使用当周期输入；index、offset 和操作属性来自上一拍缓冲。该历史稳定性要求不被重新解释成新 ready-valid 协议。
- 两路同时命中时，读数据按位 OR；测试不得假定只取低路。
- uncache 强制 miss，读类型为 `3'b010`，地址保留原 offset；cache line 读类型为 `3'b100`，地址按 16-byte 对齐。
- miss 优先选低编号 invalid way；两路均 valid 时使用 8-bit LFSR 的 bit 6 选择 way 0/1。

## Miss、refill 与取消

- replace 状态保持 `rd_req`，直到 `rd_rdy`；refill 对每个 `ret_valid` 递增 2-bit beat 号。
- cache line 的四个返回 beat 分别写四个 bank，最后一拍写 tag/valid；uncache 返回不修改 SRAM。
- 请求 offset 对应 beat 或 uncache 的任一返回拍产生 `data_ok`，`rdata` 直接旁路 `ret_data`。
- lookup 中 `tlb_excp_cancel_req` 返回 idle 并在同拍产生 `data_ok`；已进入 replace/refill 后该信号不取消事务。
- `cache_miss` 按历史代码只检查可缓存 refill 与 `ret_last`，不额外检查 `ret_valid`；上游正常协议会令 last 与 valid 同拍，但随机 gate 也覆盖非协议输入以锁定该逻辑。

## CACOP 与遗留死端口

当前重构分支以历史最后通过点 `d22c13c` 作为 CACOP recovery oracle：CACOP mode 0/1/2 不得伪装成普通 cache hit 或在 lookup 立即返回 `data_ok`，而应进入既有 replace/refill 状态路径；命中/未命中的 tag、dirty 和 AXI 副作用按该 oracle 逐拍比较。锁定 `a158aa8` 的 bypass 行为已在 `0x1c07c79c` 复现为失败，不能继续作为正确性合同。

`wr_req` 仅在 reset 时被置零，`wr_type/wr_addr/wr_wstrb/wr_data` 在 golden 中完全未驱动，`wr_rdy` 未消费。候选在 reset 后将这些兼容死端口确定为零；这是 2-state 官方仿真兼容，不声明四态逐位等价。

I-cache 没有 PRELD 端口；PRELD 属于活动 D-cache 边界，本迭代不伪造相关覆盖。

## 差分观察窗口

逐拍比较所有有定义输出：`addr_ok/data_ok/rdata/icache_unbusy/rd_req/rd_type/rd_addr/cache_miss`，以及 reset 后的 write 兼容输出。轨迹覆盖同步 SRAM 预取、连续 hit、两路冲突、miss/refill、AR backpressure、返回间隙、uncache、TLB cancel、CACOP 三种 mode、随机 reset 和连续请求。

测试必须包含会被 oracle 检出的负控。单模块 mixed overlay 的 `func_lab19` 仅用于判断是否早于已知 baseline 分歧，不得外推为 58/81、随机 DiffTest、性能、Linux 或 FPGA PASS。

## 活动 32 KiB profile

独立 `icache` 叶级生成器默认仍使用 2 way x 256 set x 16 byte（8 KiB），保留上述 golden
差分边界。活动 `SpinalCoreBackend` 使用 2 way x 1024 set x 16 byte（32 KiB），但保持原 34-port
外部接口：`index[7:0]` 与物理 `tag[1:0]` 组成 10-bit set index，tag SRAM 只保存
`tag[19:2]`。refill 地址必须由完整物理 tag、外部 index 和零 line offset 重建。

活动 profile 保留 VIPT 的单拍命中路径。请求接受拍以当前虚拟地址 `vaddr[13:12]` 预测同步
SRAM set，lookup 拍以地址翻译返回的物理 `tag[1:0]` 核验。颜色一致时不增加延迟；颜色不一致
时不得产生 `addr_ok`、`data_ok`、替换或 refill 副作用，而要保存完整物理 tag 并对正确 set 重读
一拍。物理 tag 始终是体系结构权威，虚拟色只能作为性能提示。定向测试必须预置一个错误颜色
的可命中旧行，证明旧指令不会逸出，并证明两个仅物理颜色不同的 line 可同时保留。

同步 reset 释放后，活动 I-cache 与 D-cache 并行逐 set 清除全部 tag-valid；scrub 期间
`addr_ok=false`、`icache_unbusy=false`，不得接受取指或 CACOP。数据 SRAM 不清零，因为恢复
请求前所有 tag-valid 已失效。CACOP 必须用其独立物理地址发起同步 tag probe，不能沿用前一条
取指的 set；尤其 mode 2 命中失效要有跨 set 定向测试。

32 KiB profile 的正确性证据不能从 8 KiB 叶级差分外推。采纳前必须同时通过错误颜色 replay、
reset scrub、跨 set CACOP、完整核心 DiffTest、连续 perf20、Vivado 时序/DRC 和真实 FPGA 重复
测试。
