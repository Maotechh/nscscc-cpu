# 20260713-0613-core-contracts

- 状态：`draft / implementation_in_review / awaiting_push`
- 分支 / Base SHA / implementation SHA：`refactor/20260713-0613-core-contracts` / `1e3a501ef90d2ec5a397b31e2a43e3e69aeec22c` / `5848f94a331ff2064a36a1ddc7a5e0b438e24964`
- Owner / Agent：Codex + parallel contract owners
- 目标边界：冻结 CoreConfig、流水、memory/AXI、commit/ArchState typed contracts

## 选择理由

兼容壳已建立，继续串行迁移叶子会拖慢整机。四个 owner 需要同一个可编译、可核对 golden 位序的公共合同；本轮只建立这项 prerequisite，不混入行为模块或性能优化。

## Golden 与限制

四条 legacy packed bus 为 109/350/425/493 bit；LACC-on decode 为 353 bit。LACC 宏来自锁定上游 header，因为 `a158aa8` tree 自身缺少 header。当前旧 `Pipeline.scala`、`AxiBridge.scala`、`CSR/TLB/Cache/BTB` 均不作为 golden implementation 复用。

`reference/pipeline-layouts.tsv` 的 143 个字段记录由 Python 直接对照四段 golden concat；Scala 另以该 oracle 的 digest、逐字段 slice 比较和 128 轮全位随机验证 pack/unpack。I-cache 只允许 line read，D-cache 使用独立 read/write contract；PRELD/CACOP 是不欠 response 的单向命令。

## 并行 ownership

- config/pipeline payload：独立 owner。
- memory/line/AXI3 contracts：独立 owner。
- CommitEvent/ArchState：独立 owner。
- PipelineCtrl、合同集成、日志和最终门禁：主线程。

## 修改与行为合同

- 新增 fail-closed `CoreConfig` 和 LACC × DiffTest 四配置真实 elaboration probe；活动 ISA/debug 只允许锁定开启值。
- 新增五级 directionless payload、golden 位序 oracle、`PipelineCtrl` 和 EX/MEM/WB occupancy。
- 新增 CPU memory、I/D line、barrier status 与 AXI3/WID 五通道 typed contract。
- 新增一次性 `CommitEvent`、32 GPR + 27 CSR `ArchState`，包含官方 counter/CSR/load/store/TLB 观测字段。
- 活动 `core_top` backend 未切换，因此本轮不产生功能、性能、资源或 Vivado 实现增量。

## 失败尝试与修复

- 初版缺少独立逐字段 oracle；补 `pipeline-layouts.tsv` 后 Python 先出现 2 个预期 RED，再达到 8/8。
- 首轮统一 Scala gate 因 3 个格式问题失败；随后发现端口空白正则和 memory 字段 digest 不一致并修复。
- 一次运行 4/4 task 通过但总 gate 因新增仿真未满足 `-Wall` policy 失败；补 warning flags 后又由未使用 clock/reset warning 真实阻断，加入可观测 heartbeat/sideband 后关闭。
- 最终复审要求 CACOP 与 PRELD 同为单向命令，并要求 pack/unpack 逐字段直接绑定 oracle；新增测试首轮因误把 `elements` 当 Map 编译失败，修正后最终 locked Scala gate 4/4 PASS。
- WSL detached 临时 clone 的 doctor 因无分支而失败，不作为有效 gate；真实 Windows worktree doctor 19/19 PASS。
- Windows automation 有 10 个平台权限/文件系统 skip，不接受为最终证据；POSIX WSL 重跑 304/304、0 skip。
- Claude 两次均在模型执行前失败：第一次 backend 禁止 reviewer tools，第二次缺少 `GEEKPIE_CLAUDE_API_KEY`；已降级为两轮独立只读本地审核。

## 门禁结果

- doctor：19/19 PASS，Vivado 2023.2 launcher/binary hash 与 batch probe PASS。
- contract parser：8/8 PASS。
- Scala：format/compile/test-compile/test 4/4 PASS，18 tests，0 skip；6 个 Verilator script warning policy PASS。
- elaboration matrix：LACC off/on × DiffTest off/on 4/4 真实生成。
- repository automation：POSIX 304/304 PASS，0 skip。
- 功能、random、perf、Linux、FPGA：未执行；本轮没有切换活动 backend，不能从合同门禁推导这些 claim。

## 残余风险

- 活动 CPU 仍是 legacy Verilog；本轮只解除并行行为迁移的公共合同阻塞。
- Golden WB 在 breakpoint stall 时以 level `ws_valid` 触发副作用，可能重复提交；WB 迁移前必须独立 ADR 决定严格复现或 bugfix。
- Golden TLB 和部分 CSR 状态无 reset；迁移不能擅自初始化为零。
- `func_lab19` baseline 仍在 `0x1c07c79c` 失败；后续 mixed overlay 只能比较是否引入更早偏差。

## 下一批无阻塞候选

- `csr` exact legacy overlay：最快的活动特权竖切。
- `axi_bridge` exact legacy overlay：最快的活动存储竖切。
- pipeline stage exact wrapper/harness，先解决 WB breakpoint 决策并并行推进 EX/MEM。

## 回退

revert 本 prerequisite PR 即可；它不切换活动 CPU backend，不改变参赛稳定线。

PR：未自动创建或合并。首次 push 在 48.7 秒后因 GitHub connection reset 失败，状态保持 `awaiting_push`。
