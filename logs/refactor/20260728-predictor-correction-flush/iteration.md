# Registered response-level predictor correction

日期：2026-07-28

## 目标与 routed 证据

提交 `26925beb9bbe70ae3312da39e39fc7fefbc3e133` 的锁定完整 SoC 结果为 WNS/TNS
`-0.170742/-8.018137 ns`，122 个 setup failing endpoints。最差 CPU 路径从 L1I
response predecode 出发，经 response-level prediction correction 和 predictor flush，
到 speculative RAS restore；`9.801 ns` 数据延迟中 `6.727 ns`（68.6%）为布线。

ysyx `la32r-linux` 的 IFU 先把 `fixRedirect` 寄存，再向 BPU/RAS 发出 flush。本轮采用
相同边界，但保留立即修正 frontend PC 的行为，只把 GHR/RAS 恢复延迟一拍。

## 保留的实现

- `predictionCorrectionOnResponse` 仍在 cache response 拍阻止错误 cached handoff、修正
  `nextFetchPc`，并排空已接受且不可取消的 uncached 请求。
- 新增单拍 `predictionCorrectionFlushPending`，下一拍才恢复 predictor 的 speculative
  GHR/RAS，切断 L1I predecode 到 RAS register enable 的组合路径。
- predictor 恢复拍禁止新的 translation lookup。否则同步 predictor 会使用恢复前的
  speculative GHR 发起请求，产生协议正确但历史错误的预测。
- architectural redirect 仍立即 flush，不增加异常、ERTN 或 branch completion 恢复延迟。

## 功能与生成门禁

| 检查 | 结果 |
| --- | --- |
| Frontend 定向测试 | 12/12 passed，cached/uncached correction 均覆盖恢复拍 lookup bubble |
| Scala/Spinal/Verilator 全量 | 36 suites，130/130 passed |
| Python repository gates | 362/362 passed |
| package/port/Yosys/publish | 全部通过，49 ports、41 design modules、`TLBNUM=32` |
| exact generated-top lint | 853 条，仅 `CMPCONST`/`UNUSEDSIGNAL`，精确 closure 通过 |
| lint signature | `5c7dc1c4b5d8261b216d5a2222fef205d17d133ad9175ad18efc188e3985e836` |
| generated RTL SHA-256 | `855f2c8173027d3c4a8e4f651bb6179afa576af25f780d9db5ee2f10d5bb827a` |

官方 Chiplab `func/func_lab19` 在显式清除旧 `obj_dir/output`、重新执行 Verilator、
testbench 和软件编译后通过 NEMU DiffTest，以 `END by Syscall` 结束并到达 end PC：
139,670 instructions / 555,322 clocks / IPC 0.251512。相对 `26925be` 的 552,247 clocks
增加 3,075 clocks（0.557%）。该差值对应 response-level correction 的恢复拍气泡，
只有完整 SoC 因此闭合 100 MHz 才值得保留。

验证目录缺少 `toolchains/qemu/qemu-system-loongson32`，因此可选的 golden trace 生成未执行；
NEMU DPI DiffTest 正常加载并完成，不影响上述三项结束判据。

## Standalone Vivado 证据

Vivado 2023.2、`xc7a200tfbg676-2`、10 ns、`general.maxThreads=8`：

- WNS `+0.419 ns`、TNS `0 ns`、0 setup failing endpoints；
- 72,315 LUT、39,679 FF、58 RAMB36、16 RAMB18、4 DSP；
- `timing.rpt` SHA-256 `75567b9ce3aa15d0af5ac6215055cc82c91e3044ec6715de1210af546039005b`；
- `utilization.rpt` SHA-256 `359fd1a64d1fd395202cfd9c471fa0b5173d248fe1058d9b18670be050348ba8`；
- `drc.rpt` SHA-256 `2b1387985eeb6dff6576ef38fccc7a0e6fb1c57b62d7ddc2de6124dc683970ae`；
- DCP SHA-256 `f8f364259a6ae34b70a828ffc81c7856b9b2416038e191ac1fa82495bc5eb778`。

standalone 结果不含官方 SoC placement、routing 和板级 XDC。

## 决策门禁

精确提交并推送后执行完整 SoC `perf20@100MHz` implementation。若 routed WNS 非负，
再进行三次真实 `perf20`；若仍为负，按新的 routed worst path 继续迭代。该候选有明确
周期代价，在完整 SoC 未证明时序收益前不能晋升为性能基线。
