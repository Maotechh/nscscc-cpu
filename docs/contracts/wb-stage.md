# openLA500 写回级迁移合同

## 固定来源

- Golden candidate：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/wb_stage.v`
- Golden Git blob：`90ae54b4ea13298aa64ee83aa33eee14813392d7`
- Golden SHA256：`8a6f6cb282d152e4b43673397b8c00f598e3d116589e5797fb6feaadbc032a09`
- `csr.h` 也固定到同一提交，SHA256 为
  `11f5550b887a2b507a5b916340069d6d127848c66c761f07d0303c7cc201026d`。
- `MS_TO_WS_BUS_WD=493`，`WS_TO_RF_BUS_WD=38`。
- 时钟为 `clk` 上升沿，`reset` 为高有效同步复位。
- 普通配置为 52 个端口；`DIFFTEST_EN` 配置额外导出 12 个观察端口，共 64 个。

`a158aa8` 仍是待整机验证的 golden candidate。本合同只锁定新旧写回级在所列输入轨迹下的局部等价，不把它提升为 ISA 正确性规范。

## 行为边界

1. 写回级只有一个槽位。`ws_allowin = !ws_valid || !debug_break_point`；断点停顿时必须保持 `ws_valid` 和已锁存的 493-bit payload。
2. `reset` 或写回级自身产生的 exception/ERTN/refetch/icacop/idle flush 清除有效位；flush 优先于同拍新输入。
3. GPR、CSR、TLB、LL/SC、性能事件和 debug 输出必须由锁存 payload 产生。异常指令不得形成 `real_valid`、GPR/CSR 写回或正常退休事件。
4. 16-bit exception vector 按原 RTL 优先级产生 ECODE、ESUBCODE、BADV、TLB refill 和 TLB exception 信息。
5. 普通配置不得出现 DiffTest 端口；`DIFFTEST_EN` 只增加观察端口，不改变普通端口和状态转移。
6. DiffTest 的 timer、load/store、CSR 和地址/数据 payload 来自当前锁存的写回 payload。测试必须在 breakpoint backpressure 期间持续比较这些信号，不能改为比较正在变化的 `ms_to_ws_bus`。

## 自动化证据

- `make wb-stage-contract`：校验 manifest、golden blob、`csr.h` 和合同 schema。
- `make generate TARGET=wb_stage`：分别生成普通与 DiffTest RTL，并做两次可复现 elaboration。
- `make port-check TARGET=wb_stage`：分别检查 52/64 个端口的名称、方向和宽度。
- `make lint TARGET=wb_stage`、`make yosys-check TARGET=wb_stage`：对两个 profile 执行 Verilator/Yosys 静态检查；未批准 warning 失败。
- `make unit TARGET=wb_stage`：在 `DIFFTEST_EN` profile 下进行不少于 8192 拍 directed/random 锁步，比较全部普通和 DiffTest 输出；随后运行故意翻转 candidate `debug_ws_valid` 的负控并要求报告首个 mismatch。

这些 gate 不代替活动 `core_top` 集成、官方 func、随机 NEMU DiffTest、性能、Linux 或 FPGA 结果。
