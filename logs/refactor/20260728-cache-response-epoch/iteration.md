# Cache response recovery epoch

## 目标

修复提交 `e68b4929050953b5d8e5cfeae92cb8a888684896` 在真实 `perf20@100MHz` 中稳定出现的 `quick_sort` 功能失败，同时保持四发射、五写回、三提交乱序结构和已有非阻塞 cache/MSHR 行为。

## 失效模式与根因

上一提交的三次真实板测均为 19/20，唯一失败项为 `quick_sort`。该程序同时具有高分支恢复频率、load/store 压力和真实 DDR 延迟，暴露了本地短延迟仿真没有覆盖的身份复用窗口：

1. speculative load 的 cache request 已被接受后发生 branch recovery；LSQ 清除该 load，但已进入 cache/MSHR/AXI 的请求不能取消。
2. ROB/LDQ 环形槽位之后可以被新 load 复用。
3. 旧实现的 cache response 只携带 ROB pointer。旧 DDR response 若在复用后返回，可能误命中新 load 并写入错误数据。

ROB uop 已有 8-bit `recoveryEpoch`，但原 cache request/response contract 没有携带它。这不是 MSHR 并发策略本身的问题，而是事务身份在 memory hierarchy 边界被截断。

## 实现

- `OooCacheRequest` 和 `OooCacheResponse` 增加 `recoveryEpoch`。
- LSQ 发出 load request 时保存 epoch，完成匹配改为 `robPointer && recoveryEpoch`。
- L1D hit、MSHR waiter/refill 和 uncached AXI read context 原样传递 epoch。
- 增加定向测试：旧 epoch 的 load 发出后 flush，新 epoch 复用相同 ROB pointer；旧 response 必须被拒绝，只有新 response 能完成。
- 删除 AXI bridge 中完全未读取的 `dataWriteContext`，因此完整顶层 lint 审计项从 853 减少到 844。

## 本地门禁

| 门禁 | 结果 |
| --- | --- |
| Scala/Spinal/Verilator | 36 suites，131/131 passed |
| Python repository gates | 362/362 passed |
| 端口、Yosys、publish | 全部通过 |
| 完整顶层 lint | 844 项精确审计后 0 warning/error |
| 生成 RTL SHA-256 | `433720b1a3d2b10018b858aef10d14ca75ada631e4718bb605c9f411349a698d` |

官方 Chiplab `perf/quick_sort` 仿真结果：

| AXI 延迟 | 结果 | SoC count | CPU count |
| --- | --- | ---: | ---: |
| 固定 | PASS | `0x312804` | `0x31273f` |
| random seed `5570815` | PASS | `0x312c0f` | `0x312b40` |
| random seed `20260728` | PASS | `0x312c4b` | `0x312b69` |
| random seed `8675309` | PASS | `0x312b1f` | `0x312a4e` |

随机延迟证据目录位于 `/home/ubuntu/nscscc-lsu-ready-2a4c6d85/validation/epoch-response-20260728`，在仓库外保存，避免把仿真缓存和大文件提交到源码树。

## Vivado 2023.2

独立 `core_top` 使用 `xc7a200tfbg676-2`、10 ns 约束和 `general.maxThreads=8`：

- WNS `+0.279 ns`，TNS `0 ns`，setup failing endpoints 0。
- 72,689 LUT、39,794 FF、58 RAMB36、16 RAMB18、4 DSP。
- `timing.rpt` SHA-256：`E0641970EC9DC6EB4295BBAB88C98632A97B083A4976467D8BFB8906FEEC7CC8`。
- `utilization.rpt` SHA-256：`4BD35D2C088412061ECF461DD1B60F65DE8505CA54B1F9A53CB99CFB6155DF3B`。
- DCP SHA-256：`7146EA826AEAE4EF83B67D04DC70C6130C8A5369783FF7DB1CD1728CBCB862F1`。

独立顶层没有板级 XDC，因此 NSTD-1/UCIO-1 仍是预期的 critical warning；完整 SoC implementation 的 WNS、DRC 和 bitstream 才决定 100 MHz 是否闭合。

## 合规审核

- CPU 逻辑只修改 Scala/SpinalHDL 源码，`rtl/mycpu_top.v` 由 `make generate-core` 自动生成，没有手写或手改 Verilog。
- 修复使用通用事务代际身份，不检查程序名、PC、数据值或 benchmark 地址，不含 quicksort 特判。
- 没有修改官方 reference、SoC、测试程序或计数器语义。

## 待完成

1. 提交并推送精确 40 位 revision，供锁定构建器从远端获取。
2. 构建完整 `perf20@100MHz` `.fpgajob`，确认 implementation 完成、DRC 0 error 和数值 WNS。
3. 执行三次真实板测，分别校验 package 与返回 artifacts SHA-256。
4. 只有三次结果均确认 quicksort 修复后，才用实际计数报告 perf20 用时；本地估算不是决定性性能证据。
