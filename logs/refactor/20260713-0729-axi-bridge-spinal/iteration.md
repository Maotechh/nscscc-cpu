# 20260713-0729-axi-bridge-spinal

- 状态：`draft / differential_pass`
- 分支：`refactor/20260713-0729-axi-bridge-spinal`
- Base SHA：`f621c7a1e056b9f128b86efddbdd2598b3692ecc`
- Implementation / tested SHA：`bb2dbff743216e83eeb15f98f0651f717c1b4cc8`
- Evidence Head SHA：待证据提交
- Owner / Agent：Codex（memory）
- 选择边界：活动 `a158aa8:rtl/axi_bridge.v`
- 选择原因：该桥是 I/D Cache 进入官方 AXI3/WID 的唯一活动转换点；完成它可以解除存储系统纵向集成阻塞，并且 golden RTL 可独立逐拍执行。
- Golden：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/axi_bridge.v`，Git blob `4219790c25c653da1a061c5f4c674e062201b8e9`
- 锁定工具：Scala 2.13.16、sbt 1.10.11、SpinalHDL 1.14.2、Verilator 5.020、Yosys 0.33、Vivado 2023.2
- 行为合同：`docs/contracts/axi-bridge.md`
- 修改文件：Spinal 状态机与 generator、锁定合同/生成 RTL/overlay spec、统一 Make 入口、差分 gate 与自动化测试、本轮日志和状态源
- 尝试与失败：见下文；失败尝试同时保留在 `commands.jsonl`
- 命令与门禁：本地 change-impact gate 已通过，官方 overlay/func 与 claim review 待 committed revision
- 功能/性能/资源变化：不做性能优化；只要求历史周期行为兼容
- 残余风险：golden baseline 与 mixed 的 `func_lab19` 均在 `0x1c07c79c` 失败；单模块一致不得扩展为整机 PASS
- 回退：revert 本迭代 PR，恢复 golden `rtl/axi_bridge.v` overlay
- PR：`awaiting_push`；不自动创建、标记 ready 或合并 PR
- 下一候选：I/D Cache 与新桥的 typed contract 集成

## 行为边界

本轮保留 65 个 legacy 端口、data-read 优先仲裁、写响应期间阻塞读请求、AXI3 WID、固定 INCR 属性、读响应零反压、scalar/四拍 cache-line 写、AW 先于 W 的状态顺序、`write_buffer_empty` 和未使用的 instruction-write 兼容端口。`bid/bresp/rresp` 仍与 golden 一样不参与控制。

## 尝试与失败

1. 在 Windows worktree 直接调用 WSL Scala gate 时，WSL 无法解析 `.git` 中的 `D:/.../worktrees` 指针而 fail-closed；改为同 base 的 WSL-native 临时 clone 后执行，没有修改原 Git metadata。
2. 首次 Scala compile 报 `clockDomain` 与 `Component` 成员重名，且两个新文件未格式化；重命名为 `bridgeClockDomain` 并用锁定 scalafmt 机械格式化后四项通过。
3. 首次 generation 因 `rready` 是只有 reset 赋值的 hold register，Spinal 首轮 phase 报 unassigned register 并留下 `SpinalExit` marker；加入显式自保持后两次生成通过，不把异常当成功。
4. 首次 cycle diff 在第 1 拍比较了 `awvalid=0/wvalid=0` 时未复位的 payload。合同本来明确排除此窗口；driver 改成仅在对应 valid 为 1 时观察 payload，RTL未为迎合测试添加伪复位。重跑 8192 拍为 0 mismatch。
5. 首次 `make elaborate TARGET=axi_bridge` 误传 `--runs 1`，通用 generator 按可复现策略拒绝；修成两次后通过。

## 本地门禁

| Gate | 结果 | 摘要 |
|---|---|---|
| Windows doctor | PASS | 分支保护、manifest、Vivado ML Standard 2023.2 binary/hash/version 均匹配 |
| chiplab doctor | PASS | `a2e11b3`、myCPU `aa3bde1`、Verilator 5.020、Yosys 0.33、JDK 17.0.19 及工具哈希匹配 |
| Automation | PASS | 308/308，包含 4 个 AXI bridge contract/negative-control 单测 |
| Scala | PASS | format/compile/test-compile/test 4/4 |
| Contract / ports | PASS | golden blob、10106 bytes、65/65 exact ports |
| Elaboration / generation | PASS | 各两次；生成字节可复现，RTL SHA256 `4c307033...e70a0` |
| Verilator / Yosys | PASS | 仅对精确 dead compatibility ports 使用 scoped `UNUSEDSIGNAL` waiver；其余 0 warning，hierarchy/check PASS |
| Cycle differential | PASS | seed `0x158aa8`，8192 拍，golden/candidate trace SHA256 同为 `d940e413...e93f8`，0 mismatch |
| Oracle negative controls | PASS | 禁用 data-read、错误 line len、禁用 AW handshake 三项分别在第 3、3、10 拍被检出 |

差分包含 directed reset/双读优先级/AR backpressure/scalar 写/line 写/W backpressure/B 完成沿接读，并在其余周期随机化 AR/AW/W/B/R 延迟与请求。它是固定 2-state cycle evidence，不是所有输入序列的形式等价证明。

## 官方 chiplab 诊断

从 clean committed `bb2dbff` 创建两个隔离 overlay：locked 是 0 replacement 且 gate eligible；mixed 只从同一提交的 Git blob 替换 `rtl/axi_bridge.v`，安装 SHA256 为 `4c307033...e70a0`，模式按规定为 diagnostic。

两侧都实际执行 `func/func_lab19`，结果均为 1 executed / 1 failed / 0 skipped；首错均为 PC `0x1c07c79c` 的 t0，expected `0x6e2`、actual `0x8`，均为 172552 instructions / 602903 cycles，trace SHA256 均为 `8efa7942...38acb`。locked warning 为 644（DUT 280 + official 364），mixed 为 641（DUT 277 + official 364）。因此 func 和 identity gate 均为 FAIL，只支持“该已知失败 case 没有更早的选定可观察分岔”。

首次 mixed overlay 因临时 source clone 处于 detached HEAD 被 fail-closed 拒绝；创建指向同一 SHA 的同名 `refactor/*` 分支后，clean branch/provenance 检查通过。没有放宽 overlay oracle。

## Review 与远端

Claude review MCP 在本会话未暴露，模型没有启动，状态记录为 `unavailable`。执行代理只做了本地 artifact/claim consistency audit，不冒充独立或 Claude 审核。Implementation commit 的首次 GitHub push 因 443 连接失败，分支保持 `awaiting_push`，后续重试；没有创建或合并 PR。

## 独立 Claim 审计

`/root/axi_audit_finish` 在不修改实现 RTL 的只读副本中复核了端口、复位/周期、overlay provenance 和 driver masking。除原始 `0x158aa8` 外，seed `0x1`、`0xdeadbeef`、`0xc001d00d`、`0x7fffffff` 各执行 8192 拍，均为 0 mismatch 且三项负控均检出；在 0/1/2、40/41、150/151、300/301、500 拍插入同步高有效复位的 2048 拍轨迹也与 golden SHA256 一致。AR/AW/W payload 只在 valid 窗口比较，握手和返回信号未被 masking。机器可读证据见 `evidence/independent-claim-audit.json`，独立结论见 `reviews/independent-claim-audit.md`。

该审计只扩大有限 2-state 仿真覆盖，不改变官方 `func_lab19` 失败、warning/identity 失败、Claude 不可用和未推送等阻塞项。

## 未执行

- 本轮不执行 58/81、multi-seed DiffTest、perf、U-Boot、Linux、Vivado implementation/bitstream 或远端上板。
