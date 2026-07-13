# MEM stage 行为合同

## 固定接口

- Golden candidate：`a158aa8:rtl/mem_stage.v`，blob `ebeacf81c498b3041f5c55b16c2abe220e87ecd4`。
- 模块名固定为 `mem_stage`，普通配置共 49 个端口；该模块没有 `DIFFTEST_EN` 条件端口。
- `ES_TO_MS_BUS_WD=425`、`MS_TO_WS_BUS_WD=493`、`MS_TO_DS_FORWARD_BUS=39`。
- `reset` 是与 `clk` 同步的高有效复位。

`a158aa8` 仍是待整机验证的 golden candidate。本合同只证明给定输入轨迹上的局部周期等价，不把它提升为 LA32R 正确性规范。

## 行为边界

1. MEM 是一个单槽位流水级。`ms_allowin = !ms_valid || (ms_ready_go && ws_allowin)`；停顿时必须保持已锁存的 425-bit payload。
2. load/store 只有在 `data_data_ok`、已缓存 response、异常或 SC cancel 时才能离开。cache response 在 WB backpressure 期间必须锁存，后续 live `data_rdata` 变化不得污染结果。
3. load byte/half/word 的地址选择、符号扩展，以及 mul/div/mod 结果选择必须与 golden 逐位一致。
4. TLB refill/PIL/PIS/PPI/PME、DMW、direct-address、uncached 和 SC reservation cancel 必须保持原优先级与组合条件。
5. reset 或 exception/ERTN/refetch/icacop/idle flush 清除有效槽位。被清除的指令不得继续形成 `ms_to_ws_valid`。
6. forwarding、TLB stall、TLBEHI write、stage flush 和完整 493-bit MEM→WB payload 都是差分观察量；不能只比较最终 GPR 写回。

## 自动化证据

- `make mem-stage-contract`：校验 manifest、golden blob、`csr.h`、bus width、49 端口和合同 schema。
- `make generate TARGET=mem_stage`：两次可复现生成候选 `mem_stage.v`。
- `make port-check TARGET=mem_stage`：检查候选端口名称、方向和宽度。
- `make lint TARGET=mem_stage`、`make yosys-check TARGET=mem_stage`：未批准 warning 或结构错误失败。
- `make unit TARGET=mem_stage`：逐相位比较全部 15 个输出，覆盖 reset/flush、结果选择、load 对齐/扩展、response buffer、TLB/DMW/uncached/SC，并追加不少于 8192 个随机周期；随后故意压低 candidate 的有效输出，要求负控报告首个 mismatch。

这些 gate 不代表活动 `core_top` 集成、官方 func、随机 NEMU DiffTest、性能、Linux 或 FPGA 已通过。
