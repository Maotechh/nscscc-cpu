# Draft PR：迁移 LACC FSM 并接入活动 Spinal backend

## 行为合同

- 将 a158 `lacc_core/lacc_demo` 的四状态 FSM迁移为 Scala，保留部分同步 reset/flush 和周期级 memory/response 行为。
- 默认官方 `core_top` 保持 LACC-off；新增显式 LACC-on generator。
- LACC 请求只在 DCache `addr_ok` 推进，读响应只在 `data_ok` 消费。

## 验证

- 8192 周期 golden/candidate 两态 lockstep PASS；negative control PASS；candidate 0 warning。
- LACC directed + exact legacy ports + LACC/DCache integration 3/3 PASS。
- 完整 Scala gate 18 suites/29 tests PASS。
- LACC-off/on 各 2/2 可复现生成；49-port contract、canonical package、Yosys均PASS。
- whole-top strict lint FAIL：off 80 warnings，on 81 warnings。
- official smoke、func58/81、random、perf20、system、Vivado/FPGA未执行。

## 回退与状态

revert 本迭代提交即可恢复 LACC-off-only backend，默认归档 RTL未改变。PR必须保持 draft；本文件只作为草稿，代理不自动创建、ready 或合并 PR。
