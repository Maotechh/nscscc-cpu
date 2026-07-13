# 20260713-2119-mem-stage-spinal

- Status: `differential_pass`，等待活动 overlay 集成与官方整机门禁
- Branch / Base SHA / Head SHA: `refactor/20260713-2119-mem-stage-spinal` / `b2946f8ac93fc9ccfa9c8748bb53f444976c36cb` / 提交后补充
- Owner / Agent: pipeline / Codex + 独立 gate 子代理
- Selected boundary and selection reason: 选择活动 `mem_stage`。其 EX/MEM 与 MEM/WB 总线、TLB/DMW、load 数据整形和 backpressure 合同均可由锁定 Verilog单独执行，且能直接解除五级流水线集成的后续阻塞。
- Golden reference and locked tool versions: `a158aa8:rtl/mem_stage.v`，SHA256 `86592ed3...`; Scala 2.13.16、SBT 1.10.11、SpinalHDL 1.14.2、JDK 17.0.19、Verilator 5.020。
- Behavior contract: 49 个 legacy 端口；425-bit EX/MEM 输入、493-bit MEM/WB 输出、39-bit forwarding；同步高有效 reset；完整 load/mul/div/exception/TLB/DMW/uncached/LL-SC/flush/backpressure 逐周期行为。
- Files changed: typed `MemoryStage`、`LegacyMemoryStage`、generator、contract/gate/tests/Makefile、replacement RTL、状态和本目录日志。
- Functional/performance/resource delta: 叶子合同、静态检查和 8235 周期锁步通过；尚未运行活动 overlay、官方功能、性能或 Vivado，不能声明整机收益或无回退。
- Residual risks: 官方 `func_lab19` baseline 仍在 `0x1c07c79c` 失败；活动 overlay 集成、58/81、random DiffTest、perf、Linux 和 FPGA 均未完成。
- Rollback: revert 本迭代提交；活动 overlay 尚未引用 `mem-stage.json`，不会影响稳定线。
- PR URL or awaiting state: `awaiting_push`，推送后保持 draft 草稿，不自动创建或合并 PR。
- Next unblocked candidates: 将 `mem_stage` 加入活动 replacement overlay；并行完成 IF/ID 的 golden lockstep。

## 尝试与失败

1. 初始 Scala 编译因 `clockDomain` 缺少 `override` 失败，已修复。
2. 初始 generator 将 `--out-dir` 当作路径字面量，两轮均无产物，已补齐与 WB/EX 相同的安全参数合同。
3. 首个候选存在 TLB 异常位、符号扩展、多结果 OR、flush 和 data buffer 优先级偏差，静态逐行核对后修复。
4. 差分首错为 cycle 19 / phase 1 的非法 half-load offset 3：golden 返回 0，候选错误取低半字；保留输入域并修复实现。
5. lint 首次报告 5 个 warning；收窄内部 DMW typed contract 后只保留精确核准的两个 legacy CSR 未用位段和 `preload` 历史未消费位，`unapproved=0`。

## 最终门禁

- Scala gate: 4/4 PASS，全部 Scala tests PASS。
- Python automation: 333 tests PASS。
- 可复现生成: 2/2 PASS，RTL SHA256 `37d0cba5ca2f8e901f77aaa26e56360e9205c4732f49ecd9c3189499f03e9bb1`。
- contract / port: golden 49/49、candidate 49/49 PASS。
- Verilator lint: PASS，3 项精确 allowlist，未批准项 0。
- Yosys: hierarchy/proc/opt/check PASS。
- cycle differential: 8192 random + 43 directed/setup = 8235 cycles，每周期 3 phase 比较全部 15 输出，PASS。
- negative control: cycle 3 / phase 1 首错，`ms_to_ws_valid g=1 c=0`，PASS。

以上证据只支持“MEM 叶子在本合同覆盖范围内达到 differential pass”，不支持活动整机或完全 SpinalHDL 重构完成。
