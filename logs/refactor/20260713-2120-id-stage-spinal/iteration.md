# 20260713-2120-id-stage-spinal

- Status: `differential_pass`，尚未集成活动 `core_top`，等待 PR 评审
- Branch / Base SHA / Head SHA: `refactor/20260713-2120-id-stage-spinal` / `b2946f8ac93fc9ccfa9c8748bb53f444976c36cb` / 待提交
- Owner / Agent: pipeline / Codex
- Selected boundary and selection reason: 动态选择 ID stage；它是当前流水线中尚未迁移、且依赖已锁定 FetchPayload/DecodePayload、regfile 和 execute forwarding contract 的最小活动边界。迁移它能解除流水集成阻塞，但不改变 core_top 连接。
- Golden reference and locked tool versions: `a158aa8:rtl/id_stage.v`，blob SHA-1 `93bb0283a06a0f4e88b5c37022f550b45ea4e6ed`，blob SHA-256 `dcd896a12fda42faff9f7c1bcd43de3bbd7bb181be688b0cef21dded5e05d807`；JDK 17.0.19、Scala 2.13.16、sbt 1.10.11、SpinalHDL 1.14.2、Verilator 5.020、Yosys 0.33。
- Behavior contract: 同步高有效 reset；FetchPayload/DecodePayload 一拍寄存；flush 清除 valid；ready/allowin 背压保持 payload；完整 decode、CSR/异常、TLB/cacop/preld、LL/SC、barrier、BTB/RAS、timer/perf event 与三路 forwarding 语义。保留 golden 的 MS forwarding 分支比较 stall、debug 输出读地址和非分支 BTB target 为零等历史行为。
- Files changed: `spinal/src/main/scala/openla500/pipeline/DecodeStage.scala`、`LegacyDecodeStage.scala`、`tests/rtl/id_stage_lockstep.sv`、LACC header、`tools/id_stage_gate.py`、Makefile ID target、ID contract/replacement JSON、`reference/component-replacements/id_stage.v`、本目录日志与 `docs/refactor/status.yml`。
- Attempts and failures: 首轮 cycle harness 在 cycle 4 首次发现非分支 `btb_right_target` 错误（候选输出 `pc+imm`，golden 为 0）；修正 branch target mask 后通过。DiffTest 端口首次生成是 32 个 flattened ports，增加 generator 的 legacy array restore 后才与官方 `rf_to_diff[31:0]` 兼容。Yosys 0.33 不解析 unpacked-array top port，未将该限制伪装成直接通过。
- Commands and gate results: `make scala-check` 通过；四配置 Spinal generation 各 2/2、skipped=0、可复现；四配置各 8192 random + directed（总 8259 周期）golden/candidate lockstep 通过；四配置负控均 cycle 0 mismatch；normal/LACC Verilator lint 与 Yosys hierarchy/proc/check 通过；DiffTest Verilator lint 与 flattened Yosys projection 通过。机器结果见 `evidence/*.json`。
- Functional/performance/resource delta: 本迭代未进入活动 core_top，未运行 chiplab func-58/81、NEMU random、perf、U-Boot/Linux 或 Vivado；不得据此声称整机功能、性能或资源结果。
- Residual risks: 尚未把 replacement 接入活动 `mycpu_top`，未证明与 IF/EX/MEM/WB 集成后的握手和官方 DiffTest；LACC 仅验证 ID 端口和本地差分；Yosys unpacked-array 限制仍需 CI 固化 projection 规则。
- Rollback: revert 本迭代提交，或在活动 overlay 中移除 `id_stage` replacement spec；golden `rtl/id_stage.v` 未修改。
- PR URL or awaiting state: `awaiting_pr`（已允许 push，代理不创建/合并 PR）
- Next unblocked candidates: active overlay 加入 `id_stage` 并运行 official hierarchy/smoke；随后补充 IF/ID/EX/MEM/WB 集成 gate。
