# D-cache 行为合同

## 固定事实源

- Golden: `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/dcache.v`
- Git blob: `755b5087d0321ab5a41596465c2352dd3ee98a4e`
- SHA256: `8c9c968723710ca741bb5253cc0a1f29c9c6f9f8b3e5e2b14b69f11483e60e97`
- Size: 23305 bytes
- Port manifest: `reference/component-contracts/dcache.json`

Golden 是待复测的行为候选，不是天然正确的体系结构规范。差分通过只支持固定输入轨迹、2-state 仿真窗口内的窄范围等价。

## 时钟、复位与存储阵列

`clk` 上升沿触发，`reset` 高有效同步复位。主状态机、请求 buffer、替换 way、write buffer、`rd_req_buffer`、`wr_req` 和 LFSR 有明确复位值。`miss_buffer_ret_num` 只在 read request 被接受时赋值；`uncache_wr_buffer`、`cacop_op_mode2_hit_wr_buffer`、两路四 bank 数据 SRAM、两路 tag/valid SRAM 及 dirty array 不由 reset 清零。gate 必须先用可观察事务建立确定状态再比较，并检查中途 reset 保留这些历史状态的行为。

数据/tag SRAM 是单端口同步读。读使能关闭或写周期时输出保持；数据 bank 支持 byte mask。公开实现不得把同步读误改成组合读。

## 请求与流水接受

- 请求源是 `valid || dcacop_op_en || preld_en`。
- `addr_ok` 同时受主状态、cache hit、write buffer bank 冲突和连续 load/store 冲突约束。
- lookup 的 tag、`uncache_en` 和新请求属性包含历史跨拍依赖，不能按新的 ready-valid 直觉重解释。
- `cancel_req = tlb_excp_cancel_req || sc_cancel_req`；lookup cancel 返回 idle，已发出的 AXI 事务不被凭空取消。

## 命中、dirty 与 write buffer

- 两路 tag 同时命中时，读结果按位 OR。
- store hit 先进入一拍 write buffer，再用 `wstrb` 更新目标 bank，并把命中 way 置 dirty。
- write buffer 与新请求访问同 word，或与 CACOP 冲突时，必须保持 golden 的阻塞语义。
- 替换优先选择低编号 invalid way；均 valid 时使用锁定 8-bit LFSR 的 `random_val[0]`。

## Miss、writeback、refill 与 uncached

- dirty+valid 替换先在 `main_miss` 等待 `wr_rdy`，随后进入 replace；`wr_req` 是寄存输出，时序必须逐拍一致。
- cache line writeback 固定 type `3'b100`、16-byte 对齐地址、128-bit line 和全 byte strobe。
- uncached write 使用原 size/address/wstrb/wdata；不发 read。uncached read 使用原 size/address并只接收单 beat。
- cache refill 四 beat 写入四个 bank；store miss 在目标 beat合并 byte mask，末 beat 更新 tag/valid/dirty。
- `cache_miss` 只在 cacheable、非 CACOP、非 PRELD 的 refill last 窗口产生。

## CACOP 与 PRELD

- 当前 recovery 以历史最后通过点 `d22c13c` 为 CACOP oracle：`request_buffer_dcacop` 不得在 lookup 伪装成普通 cache hit 或立即产生 `data_ok`，而应进入既有 miss/replace/refill 状态路径；mode 0/1/2 的 tag、dirty 和 AXI 副作用按该 oracle 逐拍比较。
- 锁定 `a158aa8` 的 CACOP bypass 行为已在 `0x1c07c79c` 复现为失败；在独立 recovery PR 完成前不得把它当作正确性合同。
- PRELD 参与请求和 refill，但不产生 `data_ok`，且不计入 `cache_miss`。
- `preld_hint` 在 golden 当前活动逻辑中不改变控制；精确保留端口并以哈希绑定 waiver 处理未使用告警。

## 差分观察面

逐拍比较 `addr_ok/data_ok/dcache_empty/rd_req/wr_req/cache_miss`；`rdata` 只在 `data_ok` 有效时比较，read/write channel payload 只在对应 `rd_req/wr_req` 有效时比较。无效周期的 payload 不属于协议行为，不能作为 mismatch oracle。轨迹必须覆盖 hit load/store、write-buffer forwarding/conflict、clean/dirty miss、writeback backpressure、refill gap、uncached read/write、cancel、三种 CACOP、PRELD、随机 reset 和连续请求，并包含能被 oracle 检出的事务级负控。

本叶子通过不得外推为 MEM stage、完整 memory subsystem、官方 func、random DiffTest、性能、Linux 或 FPGA PASS。
