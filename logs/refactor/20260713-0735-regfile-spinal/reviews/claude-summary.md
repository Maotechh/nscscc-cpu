# 独立 Claim 审核结论

Claude bridge 在模型启动前不可用，以下是代理执行的本地只读审核，不冒充 Claude。

## 结论

- `OpenLa500RegFile` 的时序合同与锁定 `rtl/regfile.v` 一致：组合读、上升沿写、地址零读优先、同周期旁路、无 reset、物理 slot 0 可写。
- 4096 周期比较同时检查两个读口和 32 个 32-bit 物理寄存器，足以支持该 2-state 仿真范围内的候选等价；不能支持四态 X 语义、形式完备性或整机等价。
- Scala generator 的单文件端口变换保持 legacy `DIFFTEST_EN` unpacked-array 端口；生成物已两次字节复现。生成 RTL 的业务状态逻辑来自 Scala，但端口壳仍有确定性文本适配，不能宣称“无适配代码”。
- Verilator base/DiffTest `-Wall`、锁定 Scala 4/4、doctor 和 304 个自动化测试证据可核对；Yosys 仅非 DiffTest配置通过，DiffTest 端口解析失败必须保留为未通过。
- overlay、官方 func smoke、随机 DiffTest、Linux/Vivado implementation 尚未执行，不能将本迭代升级为 integrated/full regression。

## 必须保持的窄 claim

`supported`: 活动 regfile 在已声明 2-state 4096 周期输入集合和完整物理状态比较下通过 golden lockstep。

`partial`: 生成 RTL 可复现，两个宏配置通过 Verilator 静态检查；DiffTest Yosys 静态检查不成立。

`unsupported`: 完整 CPU 重构、整机功能、Linux、随机 DiffTest、四态形式等价、Vivado timing/bitstream。

## 阻塞项

本地审核未发现阻止首次提交的实现性问题。提交后必须运行 committed-source replacement overlay；若 overlay 或 smoke 失败，只能记录为该边界未集成，不得放宽 oracle。
