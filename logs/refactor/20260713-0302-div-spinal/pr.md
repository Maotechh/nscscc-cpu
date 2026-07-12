# Draft PR：用 SpinalHDL 重构活动 divider

## 元数据

- Iteration：`20260713-0302-div-spinal`
- Branch：`refactor/20260713-0302-div-spinal`
- Base：`46173cd421f211f8978d27e768297e26ad10fd7e`
- Review target：`9e78538c0dec08fa9fcace49e068b8bc9d4d5af1`
- 日志：`logs/refactor/20260713-0302-div-spinal/iteration.md`
- 状态：Draft；不自动创建、标记 ready 或合并

## 行为合同

用显式 `div_clk` ClockDomain 的 `OpenLa500Div` 替换 `a158aa8:rtl/div.v`，精确保留 9 端口、同步高 reset、E33/E34/E35/E36、abort/late-abort、held-high restart、除零与 signed overflow 可见行为。生成 RTL SHA256 为 `0c022398...0f349`。

## 验证

本地 contract、Scala、双生成、exact port、Verilator 0 warning、Yosys、4136 transaction cycle differential 和有限协议 formal 均通过。Golden/candidate 使用同一 driver `7fd34bfa...a28ce0` 与 vectors `754ee2e0...99ead`。

官方 locked/mixed `func_lab19` 均实际执行且均在既有 `0x1c07c79c` 失败；mixed 有 641 条未批准 warning。Vivado 2023.2 两侧 standalone synthesis rc=0，但 timing、DRC、methodology 和 warning gate 未通过。Claude review unavailable。因此 PR 必须保持 Draft。

## 影响与限制

- 叶子资源观测：golden 290 LUT/107 FF，candidate 245 LUT/107 FF；不能外推整机资源。
- 不声明 Fmax 或性能；WNS/TNS 均未收敛。
- 不改变公开 CPU、cache、CSR、TLB 或 AXI contract。
- 未执行 58/81、multi-seed、perf、U-Boot/Linux、implementation/bitstream/board。
- 回退：revert 本 PR，恢复 golden `rtl/div.v` overlay。
