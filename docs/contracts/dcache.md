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

## 活动 32 KiB profile

独立 `dcache` 叶级生成器默认仍使用上述 2 way x 256 set 行为，以保留锁定 golden 的差分
oracle。生成器为此还单独启用 `a158aa8` 的 CACOP 即时完成语义；该开关只允许用于
256-set、无 reset scrub 的叶级 oracle，活动核心不得启用。活动 `SpinalCoreBackend` 继续使用
已通过功能恢复的 `d22c13c` CACOP 状态路径，并采用 2 way x 1024 set x 16 byte（32 KiB）
profile，但不改变
35-port 外部边界：`index[7:0]` 与 `tag[1:0]` 共同组成 10-bit 物理 set index，tag SRAM 只保存
`tag[19:2]`。writeback 必须按保存的 tag、完整 set index 和零 line offset 重建原 32-bit 地址。

该边界保留原有 VIPT 时序：请求接受拍有当前虚拟 `index` 和虚拟页颜色 `vaddr[13:12]`，
物理 `tag` 来自同拍 `data_fetch` 捕获并在下一拍完成的地址翻译。活动 profile 在接受拍用当前
虚拟页颜色预测 SRAM set；lookup 拍必须用新翻译的 `tag[1:0]` 校验。颜色不一致时不得产生
`addr_ok`/`data_ok`、hit-store 或 miss/refill 副作用，而应捕获完整物理 tag、用正确 set 重读一次
同步 SRAM，随后才完成 hit/miss 判定。颜色命中保持原 lookup 延迟，跨物理颜色访问增加一拍；
uncached 请求不依赖 cache set，因此不需要重读。定向测试必须包含 stored tag 与虚拟 index
相同、仅物理颜色不同的两条 line，并强制虚拟颜色预测错误，证明错误颜色不能形成假命中、
副作用或互相覆盖。虚拟颜色只是性能提示，体系结构正确性始终由下一拍物理颜色校验保证。

活动 profile 在同步 reset 释放后串行清除 1024 个 set 的 tag-valid 和 dirty，每拍一个 set；
scrub 期间 `addr_ok=false`、`dcache_empty=false`，状态机不得接受 CPU、CACOP 或 PRELD 请求。
数据 SRAM 不必清零，因为 tag-valid 在恢复接收请求前已全部失效。该 profile 有意修复 golden 中
reset 保留 cache 历史的跨程序污染风险，因此不得声称与 golden 的中途 reset 逐拍等价；必须以
定向 scrub 测试、完整核心功能测试、连续 perf20 和真实 FPGA 重复烧录独立验证。
