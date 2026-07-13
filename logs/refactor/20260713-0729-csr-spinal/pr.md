# Draft PR: migrate active openLA500 CSR to SpinalHDL

- Branch: `refactor/20260713-0729-csr-spinal`
- Base: `f621c7a1e056b9f128b86efddbdd2598b3692ecc`
- Head: `9d319136ce20a7bf8547896fb29a58e2f86ce4f4`（evidence commit待提交）
- Iteration log: `logs/refactor/20260713-0729-csr-spinal/`

## Scope

将活动 `rtl/csr.v` 重构为 `OpenLa500Csr`，保留 `TLBNUM`、CSR 读写/旁路、timer、LLBCTL、异常输入和 DIFFTEST 状态合同。`reference/component-replacements/csr.v` 是生成并锁定的 mixed overlay，不删除 golden Verilog。

## Evidence

- Scala 4/4、automation 307/307、off/on 生成两次可复现。
- 55/55 与 81/81 exact ports；Yosys PASS；Verilator CSR 静态 PASS（8 个逐文件 legacy waiver）。
- 4174/4174 边沿、51 字段逐拍差分 PASS；CPUCFG1 负控 cycle 59 检出 mismatch。
- locked chiplab doctor PASS；mixed overlay 诊断 PASS，但 `gate_eligible=false`。
- 官方 `func_lab19` configure/build/simulation 可执行，但首次 DiffTest 在 `0x1c07c79c` 失败，且 warning policy 失败（DUT 273 / 环境 364）。

## Claims and limitations

本草稿只声称 CSR 组件级生成、接口、静态和差分证据；不声称 58/81 功能、随机、性能、U-Boot、Linux、Vivado 或完全重构。baseline 失败与 CSR 单元结果分开记录。

## Rollback and review

回退本迭代提交并移除 `csr.json` overlay 即可恢复 golden。Claude bridge 不可用，已保留 `reviews/claude-raw.md` 与 `claude-summary.json`；PR 必须保持 draft，等待人工/CI 审核。远端分支已推送，状态为 `awaiting_pr`，不自动创建或合并 PR。
