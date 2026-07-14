# 20260714-1907-lacc-spinal

- Status: `implementation_in_review`。LACC 叶子达到 `differential_pass`，整机 gate 未闭合。
- Branch / Base SHA / Head SHA: `refactor/20260714-1650-consolidated-spinal` / `2d09948802ed9bef9e63afd92061173ba5a3714b` / 提交后更新。
- Owner / Agent: Codex；两个实现/验证代理；一个独立只读 claim reviewer。
- Selected boundary and selection reason: `execute/lacc_core_and_active_integration`。LACC 是最后一个被 active backend 明确拒绝的可选活动功能，现有 Decode/Execute typed 分支和 DCache 合同足以建立最小可验证闭环。
- Golden reference and locked tool versions: `a158aa8:rtl/lacc_core.v`、`a158aa8:rtl/lacc_demo.v`；JDK 17.0.19、sbt 1.10.11、Scala 2.13.16、SpinalHDL 1.14.2、Verilator 5.020、Yosys 0.33。
- Behavior contract: `docs/contracts/lacc.md`；机器合同为 `reference/component-contracts/lacc.json`。
- Files changed: LACC Scala FSM/legacy adapter、LACC-off/on top 配置和 backend 接线、ExecuteStage 明确 flush 常量、LACC golden diff 自动化、LACC+DCache 集成测试、runtime 旧模块 suppression、状态和本日志。
- Functional/performance/resource delta: 未做性能优化。默认 LACC-off 生成 RTL SHA256 仍为 `07a2a2d9...125be1`；LACC-on 增加一个 LACC Component。未执行 Vivado，不能声明 Fmax/LUT/FF/BRAM 变化。
- Residual risks: 仅证明 Verilator 两态、合法有序读响应下的可观察周期等价；whole-top strict lint 仍失败；官方 smoke、func58/81、random、perf20、U-Boot/Linux、Vivado/FPGA 均未在本提交上通过。
- Rollback: revert 本轮提交即可恢复 LACC-off-only backend；默认稳定发布 RTL未改变。不得删除 golden reference 或放宽 oracle。
- PR URL or awaiting state: `awaiting_pr`。仅推送分支，不自动创建、ready 或合并 PR。
- Next unblocked candidates: 在同一集成分支迁移未接入的活动 `perf_counter`；提交后运行官方 diagnostic smoke；再处理整机 warning 和完整官方 gate。

## 行为与接线结论

- 配置命令捕获七位 count 和写地址并立即响应；零长度 lmadd 立即响应且不访存。
- 非零 lmadd 先后接受两次读请求，等待两个有序 read response，写回两者之和，并累计所有读响应作为最终返回值。
- LACC 的 request ready 只使用 DCache `addr_ok`；read response valid 只使用活动 LACC 请求与 DCache `data_ok`；返回数据来自 DCache `rdata`。
- 最终 LACC response 与最后一次写请求的 `addr_ok` 握手同周期。集成测试没有把延后的 DCache `data_ok` 当成写请求完成条件。
- 默认官方 generator 保持 LACC-off；`GenerateCoreTopCompatWithLacc` 显式生成 LACC-on 配置。
- a158 的 `lacc_req_ready` 输入未被 exe_stage 活动逻辑消费；当前 typed ExecuteStage 不据此推进状态，whole-top LACC-on 因保留该兼容输入多一条 `UNUSEDSIGNAL`。

## 通过的门禁

1. `make lacc-contract OUT_DIR=build/lacc-main-contract`：18 端口合同、golden commit/hash、8192 周期与 seed policy PASS。
2. `make generate TARGET=lacc OUT_DIR=build/lacc-final-stable`：2/2 可复现生成，source/manifest/toolchain stable，RTL SHA256 `6f6d57014bcb893f88b07c30a00dbffa18614c6766bc17f168fef1e7bc4509d8`。
3. `make unit TARGET=lacc ...`：8192 周期 lockstep PASS；requests=145、responses=39、data=56、reads=30、writes=15、stalls=11、drsp=30、resets=11、flushes=32；negative control 在 cycle 0 捕获；candidate lint 0 warning。
4. LACC Scala directed 与 legacy 18-port generator：2/2 PASS。LACC+DCache 跨 line miss/refill：1/1 PASS。
5. 临时 clean clone 中 `make scala-check`：scalafmt、compile、test-compile、test 全部 PASS；18 suites、29 tests、0 failed/skipped/ignored/pending，未发现未批准 warning。
6. LACC-off/LACC-on `core_top`：两个 profile 各 2/2 可复现 elaboration PASS；生成物分别 19/20 modules。
7. 锁定 `core_top` 49-port contract PASS；off/on canonical package PASS；off/on Yosys hierarchy/check 均 PASS，0 warning。
8. Python LACC gate 自动化：10/10 PASS；`git diff --check` PASS。

## 失败与修复记录

1. `make port-check TARGET=id_stage` 不存在，退出 2；没有把未实现 target 写成已通过。
2. canonical moved worktree 的 Windows `.git` 指针在 WSL 下不可解析，早期 ID unit/scala gate 失败；LACC gate 增加只读指针转换，完整 Scala gate改在同 SHA 临时 clean clone 运行。
3. raw LACC-on `core_top.v` 未 package 时缺 `TLBNUM`，静态 gate拒绝；后续只对 canonical packaged RTL运行静态检查。
4. 首次 package/contract 以及本轮三项重跑均因 WSL `git status` 30 秒超时失败；改用 `2d09948` clean clone 中相同 SHA256 的 `core_top_gate.py` 后 PASS。
5. 首次稳定 LACC 双生成期间并行代理修改 Scala test，`source_stable` fail-closed；格式化并冻结源码后重跑 2/2 PASS。
6. 首次正式 LACC unit 的测试台覆盖计数被 Verilator 优化为常量，coverage policy 拒绝；把覆盖计数移到主随机循环后，positive 与 negative control 均通过。该失败不是 RTL mismatch。
7. 首次完整 `scala-check` 中 29 个测试均通过，但 LACC+DCache harness 有 8 个 pruned warning，gate整体 FAIL；harness 暴露五个 DCache 输出、动态驱动 size/preload hint，并对 golden 已知未消费的 `preld_hint` 精确 `allowPruning()` 后重跑 PASS。没有加入全局 warning 忽略。
8. whole-top strict Verilator：LACC-off FAIL（80 warnings：78 `UNUSEDSIGNAL`、1 `DECLFILENAME`、1 `UNUSEDPARAM`）；LACC-on FAIL（81 warnings，多出的唯一一条为 `io_laccInput_requestReady`）。Yosys并未失败。
9. Claude review job `faecb554a159461b8e108bac59617d90` 在执行前因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败；只能降级为独立只读代理审核，不能称为 Claude 审核。
10. 首次 `make evidence-check ITERATION_ID=20260714-1907-lacc-spinal` 因旧 `commands.jsonl` 第二条记录缺少 `cwd` 而 fail-closed；没有伪造当时未采集的耗时，相关失败仍保留在本节，机器日志只保留有真实耗时的记录。修复 schema 后复跑 PASS。

## 自动化与独立审核

- `make test-automation` 返回 0：351 项测试通过，10 项为测试套件中预设的 skip；该结果只证明自动化工具自身回归通过，不替代 RTL required gate。
- `make evidence-check ITERATION_ID=20260714-1907-lacc-spinal` 返回 0：17 条命令记录、12 个 gate、Claude 正确归类为 `unavailable`，迭代保持 `draft`。
- 独立只读审核结论为 `WARN / draft-only`，详见 `reviews/local-independent-review.md`。LACC 叶子可维持 `differential_pass`；whole-top strict lint、官方 smoke、提交锚定和 top 级 flush 合同闭合前不得提升状态。

## Claim 边界

- 允许：当前 LACC Scala FSM 在 Verilator 两态模型、合法有序 memory response、锁定 seed 的 8192 周期中，与 a158 LACC 的有效响应和 memory transaction 逐周期一致。
- 允许：当前 LACC 与 Scala DCache 的一项跨 line miss/refill 定向合同通过。
- 允许：LACC-off/on 均可复现生成 49-port `core_top`，并通过 canonical package 与 Yosys hierarchy/check。
- 禁止：四态完全等价、官方功能通过、random DiffTest 完成、整机完全重构、release-ready、Vivado/FPGA通过。
