# Candidate closure 合同

该门禁证明当前发布的 `core_top` 生成 RTL 不再定义或实例化 a158aa8 的旧 CPU
Verilog 模块。它不以文件名、代码量或 README 声明替代层级解析。

## 必须满足

- `core_top` 在发布 RTL 中恰好定义一次。
- 生成 RTL 的 module/instance 闭包中不得出现旧的 `if_stage`、`id_stage`、
  `exe_stage`、`mem_stage`、`wb_stage`、CSR/TLB、Cache、AXI、mul/div、BTB、
  perf 或 regfile 模块名。
- 未解析实例只允许锁定的 chiplab `Difftest*` 仿真边界。
- 启用 pure overlay 检查时，旧 CPU 文件必须不存在，或仅为无 module 定义的占位文件。
- 报告必须绑定发布 RTL 的 SHA256；生成物改变后必须重跑。

该门禁只证明活动层级和 overlay 输入纯度，不证明功能等价。功能、随机、系统和 FPGA
门禁仍需独立证据。
