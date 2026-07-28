# Cache 边界时序隔离

日期：2026-07-27

## 目标与起点

本轮从提交 `bd4fb1b9c97fc3272329a9eaad44d1bede61712c` 开始。该提交的锁定
100 MHz 完整 SoC implementation 已生成 bitstream 且 DRC 0 error，但 WNS/TNS 仍为
`-0.413678/-71.815697 ns`。最差路径集中在 L1D dirty line 到 L2 512-bit write-data
寄存器使能，以及 L2/AXI refill、L1I response predecode 和前端纠错形成的跨层控制锥。

CPU 保持固定 4 发射、5 回写、3 提交、64 B cache line、4-entry L1D/L2 MSHR。所有 CPU
RTL 均由 Scala/SpinalHDL 生成；`rtl/mycpu_top.v` 只是生成发布镜像。

## 保留的实现

- L2 dirty L1D line write 获得确定性优先级，`writeReady` 不再组合依赖 read valid；read
  在实际 `writeFire` 时退让，切断 L1D 状态经共享 MSHR router 返回 512-bit write-data
  寄存器使能的组合路径。
- 外部 refill 在写入 L2 beat bank 的同拍进入一项完全弹性的输出寄存器。下游消费和新
  beat 可同拍发生，因此稳定吞吐仍为一 beat/cycle；首次返回增加一拍。
- 前端允许响应纠错拍的 cached request 完成 handoff，并在下一拍同步 L1I lookup 返回前
  产生 kill。该 kill 会阻止 hit response 和 miss 分配。不可取消的 uncached AXI request
  继续使用原 response-drain 协议。
- L1I 在 request 与 kill 同拍时保存 killed 状态；同步 lookup 返回后先处理 kill/invalidate，
  不会把错误路径命中或 miss 暴露给前端。

## 放弃的同拍 kill 方案

第一版让 response predecode 生成的预测纠错同拍直接驱动 `cacheKill`。虽然定向功能测试
通过，但 standalone 100 MHz WNS 退化为 `-0.218 ns`。最差路径从 L1I response predecode
经过 predictor `nextFetchPc`、`cacheOutstanding`、`cacheKill` 和 L1I
`refillResponseSent` 又返回 response predecode，共 20 级逻辑、10.067 ns。最终方案将
cached kill 延迟到同步 lookup 返回拍，消除了该反馈锥；此中间方案没有进入发布 RTL。

## 本地功能与生成门禁

| 检查 | 结果 |
| --- | --- |
| cache/frontend 定向测试 | 4 suites，21/21 passed |
| Scala/Spinal/Verilator 全量 | 36 suites，130/130 passed |
| Python repository gates | 362/362 passed |
| package/port/Yosys/publish | 全部通过，49-port、`TLBNUM=32` 合同不变 |
| exact generated-top lint | 853 条，仅 `CMPCONST`/`UNUSEDSIGNAL`，精确 closure 通过 |
| lint signature | `5c7dc1c4b5d8261b216d5a2222fef205d17d133ad9175ad18efc188e3985e836` |
| generated RTL SHA-256 | `3b4adddff81c8978bbefdcfe38c44792a34fa8437dfd8db85a641bb181cc4263` |

官方 Chiplab `func/func_lab19` 在删除旧 `obj_dir/output`、重新执行 Verilator/testbench/
software 编译后通过 NEMU DiffTest，以 `END by Syscall` 结束并到达 end PC：139,668
instructions / 552,247 clocks / IPC 0.252909。相对已提交结果 534,497 clocks 增加 17,750
周期，即退化约 3.32%。主要代价符合 refill 输出首次增加一拍的结构预期。

## Standalone Vivado 证据

Vivado 2023.2、`xc7a200tfbg676-2`、10 ns 时钟、`general.maxThreads=8` 综合结果：

- WNS `+0.419 ns`、TNS `0 ns`、0 setup failing endpoints；
- 72,270 LUT、39,591 FF、58 RAMB36、16 RAMB18、4 DSP；
- timing report SHA-256：`21613addd95db9d9a5ad22488086f1a87df8f785af0a2514fa3760be57730873`；
- utilization report SHA-256：`7bec06769440c7dc4ff1675d7d0d0495dfe2d92750a6dc18feb03b19b287dd72`；
- DRC report SHA-256：`c38c476060bc58abaea5233710797340f4eedd6d5979a8e3a12737a541802257`；
- synthesized DCP SHA-256：`1e690414cd8242dbd08cf9e92df77684f47278bbc13f9850da97b84264fda737`。

Standalone DRC 的 NSTD-1/UCIO-1 仅因未加载板级 XDC；该综合不含官方 SoC placement、
routing 和拥塞，不能证明 100 MHz 完整时序闭合。

## 决策门禁

该候选牺牲 3.32% 本地周期来隔离完整 SoC 的已知最长路径，不能仅凭 standalone WNS
提升 `0.060 ns` 晋升为性能基线。下一步必须提交并推送精确候选，用 client 锁定构建
`perf20@100MHz` 完整 SoC：

- 若 routed WNS 非负，100 MHz 频率收益可覆盖周期退化，再执行三次真实 `perf20`；
- 若 routed WNS 仍为负，分析新的 top paths，并优先把 refill 寄存边界缩窄到 I-side 或
  直接寄存 response/predecode 状态，不保留无闭合收益的全局 refill 延迟。

功能通过、板测通过和时序闭合始终是三项独立结论。
