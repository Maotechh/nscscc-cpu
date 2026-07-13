# openLA500 CSR 迁移合同

## 固定来源

- Golden candidate：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/csr.v`
- Golden Git blob：`8d64a8af6c92b3ea0c35d10ced5e06bd12e574f8`
- 参数：`TLBNUM=32`；时钟 `clk` 上升沿；`reset` 高有效同步复位。
- 兼容模块名固定为 `csr`。普通配置 55 个端口，`DIFFTEST_EN` 配置额外导出 26 个 CSR 状态端口。

## 行为边界

1. 保留 CRMD/PRMD、ECFG/ESTAT、ERA/BADV/EENTRY、TLB CSR、ASID、DMW、页表基址、SAVE、TID、定时器、LLBit/LLAddr 和 CPUCFG 的活动行为。
2. 保留异常、ERTN、CSR 写、TLB 搜索/读取和 LL/SC 更新的原始同拍优先级。
3. 保留原 RTL 的部分复位语义；未被 reset 分支覆盖的位不得在实现中擅自增加架构初值。
4. `timer_64_out` 保留有符号扩展 `CNTC` 后相加，`rand_index` 取原始 64 位计数器低 5 位。
5. `pg_out`、`da_out`、`plv_out`、`vppn_out`、`dmw0_out` 和 `dmw1_out` 保留原 RTL 的同拍前递。
6. `DIFFTEST_EN` 只改变端口集合，不改变 CSR 状态更新逻辑。

## 验证口径

- 端口检查分别覆盖 DIFFTEST 关闭和开启配置。
- directed/random cycle differential 在相同输入、相同 reset 边沿后比较全部可见输出。
- Verilator 和 Yosys 检查必须使用生成 RTL；未执行官方整机回归时不得声明 CSR 已整机集成通过。
