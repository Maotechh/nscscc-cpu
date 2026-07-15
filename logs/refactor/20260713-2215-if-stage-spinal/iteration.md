# 20260713-2215-if-stage-spinal

- Status: `differential_pass`（等待人工评审，不自动合并）
- Branch / Base SHA / Head SHA: `refactor/20260713-2215-if-stage-spinal` / `b2946f8ac93fc9ccfa9c8748bb53f444976c36cb` / 待提交
- Owner / Agent: Codex `/root/if_stage_spinal`
- Selected boundary and selection reason: IF 是当前活动 core_top 仍依赖的最小流水边界；先建立 49 端口、109-bit payload 和 golden harness，解除后续流水集成阻塞。
- Golden reference and locked tool versions: `a158aa8:rtl/if_stage.v`；JDK 17.0.19、Scala 2.13.16、SBT 1.10.11、SpinalHDL 1.14.2、Verilator 5.020、Yosys（chiplab 工具根）。
- Behavior contract: `docs/contracts/if-stage.md`；Fetch PC、请求/响应 buffer、flush delay、branch repair、BTB lock、TLB/DMW/uncached 和 109-bit payload 与锁定 golden 对齐。
- Files changed: `FetchStage.scala`、`LegacyIfStage.scala`、`if_stage_lockstep.sv`、`if_stage_gate.py`、IF contract、replacement RTL/spec、迭代日志与审核记录。
- Attempts and failures: 初版 Stream response 方向导致 hierarchy violation；初版 BTB mux 在 cycle 1574 失配；初轮 scalafmt gate 失败；审核发现 warning 吞掉、证据仅在 `/tmp` 及 flush 状态优先级风险，均已修复并重跑。
- Commands and gate results: Scala gate 全部 PASS；Python 8 + 328 tests PASS；生成 2/2 可复现，RTL SHA256 `4d86248239becafcbbe605a4c80f059c3cacc8f2ae7d34af50b6b68fe1713b1a`；IF gate contract、warning policy、Verilator、Yosys、2048 周期 fixed-seed lockstep 和 negative control 全 PASS。
- Functional/performance/resource delta: 仅隔离 IF leaf；未运行官方 chiplab、58/81 功能、NEMU random、性能、Linux、Vivado，不能作整机 claim。
- Residual risks: fixed seed 单 trace；idle/icacop/interrupt/reset re-entry 覆盖不足；port parser 只证明 name/direction/width 集合；testbench 调试层级名依赖仍存在。
- Rollback: revert 本迭代提交；不改 `main`，不启用 `active-reachable.json` overlay。
- PR URL or awaiting state: `awaiting_push`；按要求只推送分支，不创建或合并 PR。
- Next unblocked candidates: 人工评审后，在独立迭代中补充 IF 多 seed/状态覆盖，再考虑 component overlay；不得据此跳过 core_top/流水/存储集成门禁。
