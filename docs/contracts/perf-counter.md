# Performance Counter 行为合同

## 范围与来源

本合同只覆盖锁定提交 `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6` 中活动的
`rtl/perf_counter.v`，以及 `rtl/mycpu_top.v` 对它的实例化。计数值不是 LA32R 架构状态，
也不构成官方 DiffTest 接口；迁移目标是保留活动 RTL 的逐周期内部状态和 future observation
接口，而不是新增性能功能。

## 端口合同

standalone legacy adapter 的定义名固定为 `perf_counter`，端口顺序、方向和宽度固定为：

1. `clk`，input 1 bit。
2. `reset`，input 1 bit。
3. `dcache_miss`，input 1 bit。
4. `icache_miss`，input 1 bit。
5. `commit_inst`，input 1 bit。
6. `br_inst`，input 1 bit。
7. `mem_inst`，input 1 bit。
8. `br_pre`，input 1 bit。
9. `br_pre_error`，input 1 bit。

不得向 legacy adapter 增加观测输出；typed Scala 内部可以提供只读 snapshot，供后续 perf/debug
adapter 显式消费。

## 状态与时序

- 共有七个相互独立的 32 位无符号计数器，分别对应七个事件输入。
- 每个时钟上升沿，若 `reset=1`，七个计数器全部同步清零，事件输入被忽略。
- 若 `reset=0`，每个为 1 的事件使对应计数器加一；同一周期多个事件同时生效。
- 加法为自然模 2^32 运算，`0xffffffff + 1 == 0`。
- 输入是每拍采样的 level，不是只能持续一拍的 pulse，也不是 ready/valid fire。level 连续多拍为 1
  时必须连续计数；输入不握手、不排队。本模块不改变流水 stall/flush，也不产生架构副作用。

## 活动接线

`SpinalCoreBackend` 必须在当前全部锁定配置中实例化该模块；当前 `CoreConfig` 明确只支持
`CoreConfig.isa.performanceCounters=true`，并未声称支持关闭计数器的配置。
并把 `WritebackStage.io.perf` 的七个事件一一连接。`clk` 使用唯一外部 `aclk`，`reset` 使用
`!aresetn`，且计数逻辑自身采用同步高有效 reset。

## 必需验证

- 锁定 golden blob/hash 和九端口合同。
- reset 优先级、单事件、七事件并发、空闲保持和 32 位回绕 directed case。
- 固定 seed 的逐周期随机 golden/candidate lockstep。
- 能捕获候选计数错误的 negative control。
- LACC-off/on `core_top` 可复现生成、49 端口合同和静态检查。
- 生成顶层必须包含七条 writeback-to-counter 连接；runtime overlay 必须把旧
  `rtl/perf_counter.v` 替换为 module-free 文件，避免同时携带第二份活动实现。
- 官方 smoke 只作为整机 diagnostic；通过叶子差分不得外推为 perf20 或完整重构通过。
