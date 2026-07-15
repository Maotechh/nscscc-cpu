# 20260715-1402-typed-memory

- 状态：`draft / implementation_in_review`
- 分支 / Base SHA / Head SHA：`refactor/20260715-1402-typed-memory` / `f3f61aa38f002b7a9fac3ba3feffeb2762c40707` / `待提交`
- Owner / Agent：Codex `/root/backend_arch_audit`
- 选择边界：活动 Backend 到 I/D cache、legacy AXI bridge 和外部 AXI 的连接仍直接使用 raw leaf pin。本轮只增加无状态 typed adapter，解除 memory owner 后续迁移对 raw pin 的依赖，不修改流水、cache 或 bridge 状态机。
- Golden / 固定工具：`a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6`；JDK `17.0.19+10`、SBT `1.10.11`、Scala `2.13.16`、SpinalHDL `1.14.2`、Verilator `5.020`、Yosys `0.33`。

## 行为合同与修改

- 新增 `OpenLa500TypedAxiBridge`：I/D cache 侧使用 `LineReadWritePort`，AXI 侧使用 `Axi3Compat`；adapter 不包含寄存器、FIFO、仲裁、状态机或 reset 状态。
- `OpenLa500AxiBridge` 的 cycle-compatible 状态机保持为唯一 bridge 状态 owner；typed adapter 逐字段组合映射到该 legacy leaf。
- `SpinalCoreBackend` 不再直接访问 `inst_rd_req/data_rd_req/arid/rid` 等 raw bridge pin。
- `core_top` 外部 49-port、AXI3 WID、8-bit ARLEN/AWLEN、时钟、reset、debug 和 commit 语义不变。
- 新增结构 gate 和 9 项突变负测，覆盖方向、位宽、截断、字段交换、ready 反相、表达式注入、寄存器化和注释伪造。

## 已运行门禁

- Scala：4/4 PASS，31 个 ScalaTest 全部通过，0 skip；`evidence/scala-check.json`。
- fresh generate：2/2 可重复，generator RTL `8d326e...57a9`；package `5d11d6...7d8a`，49 个端口；`evidence/generate.json`、`package.json`、`port-check.json`。
- typed bridge：结构检查 PASS，9/9 突变负测 PASS；`evidence/typed-bridge-contract.json`。
- candidate closure、publish consistency、replacement reachability、Yosys hierarchy/check 均 PASS；对应 `evidence/*.json`。
- 顺序等价：首次仅按名称匹配时 17,728 proven、95 unproven，原因是 wrapper 改变了 legacy bridge 状态层级名；加入 `equiv_struct -icells` 建立结构对应后 31,106 proven、0 unproven，exit 0。两次均保留，见 `evidence/sequential-equivalence.json`。
- Verilator strict-zero lint：FAIL，73 条既有 `DECLFILENAME/UNUSEDPARAM/UNUSEDSIGNAL`；没有新增 waiver，不得称为 rtl-static 全通过；`evidence/lint.json`。
- 自动化：wrapper exit 0，390 项中 380 执行通过、10 skip。按零 skip 合同总门禁记为 FAIL。

## 失败与外部状态

- 两次实验性 wrapper Scala 测试分别因 12 个 pruned-signal warning 和 Spinal `MULTIPLE TOPLEVEL` 失败，测试文件已删除；最终 Scala gate 回到 31 项并通过。
- `make generate` 的 2/2 生成和 package 成功，但旧 tracked package 被 publish-check 正确拒绝；发布 fresh RTL 和 hash 后 publish-check 通过。
- 首次 port-check 输出目录已存在，gate fail-closed；换用 fresh 输出目录后通过。
- 首次顺序等价没有匹配 wrapper 内 legacy 状态层级，保留为 95 unproven 的失败证据；结构对应流程随后完整证明。
- 2026-07-15 14:52 再次读取远端时 GitHub 连接被 reset；失败前一次 `ls-remote` 显示 `main=20cae5f`、`ECHO=ba4ce03`、consolidated=`f3f61aa`，live remote 本次未确认。

## 风险、回退和下一步

- 当前只支持“活动 cache/AXI 连接采用 typed contract，adapter 无状态，且 old/new generated core_top 在记录的 Yosys two-state flow 下等价”。不支持 AXI 随机 backpressure、正式 chiplab gate、58/81、random DiffTest、Linux 或 FPGA claim。
- 严格 lint、从 committed SHA 构建的 chiplab smoke、Claude claim review 尚未完成，因此状态不超过 `implementation_in_review`，PR 只能是 draft。
- 回退：revert 本迭代提交，恢复 Backend 到 `OpenLa500AxiBridge` 的直接连接和上一版发布 RTL。
- 下一步：提交并推送当前分支；从该提交建立 clean chiplab overlay，运行 pure-Spinal diagnostic smoke；执行 Claude 或明确降级的独立 claim 审核。不创建或合并 PR。
