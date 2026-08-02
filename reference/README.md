# Reference 数据

本目录保存可复现生成和官方兼容检查需要的锁定数据：

* `manifest.lock`：上游 commit、工具版本和外部环境锁。
* `core-top.ports.json`：官方 `core_top` 的 49 端口及 `TLBNUM=32` 合同。
* `golden-rtl-files.lock`：历史 golden RTL 来源 allowlist，仅供独立 leaf differential gate 使用。
* `scala-dependencies.lock.json`：Scala/SBT 依赖内容锁。
* `component-contracts/`：仍保留的 ALU、cache、mul/div 等独立 leaf 合同。
* `component-replacements/core-top.json`：生成顶层的替换哈希；逻辑目标为 `rtl/mycpu_top.v`。
* `core-top-lint-waivers.json`：锁定版 Verilator 对当前完整 RTL 的精确告警集合，只接受已审查的 `CMPCONST` 和 `UNUSEDSIGNAL` 类别。

每次 Scala RTL 变化后，在锁定工具环境中运行 `make refresh-metadata`，或从工作区根目录运行 `make cpu-locked-gates`。该流程先执行无抑制 lint 审计，拒绝新告警类别、真实错误、跳过项或工具漂移，再原子更新发布哈希和 lint 告警签名；正式 lint 随后仍会使用新签名做一次抑制闭环。

旧标量流水线的 payload layout、stage contract 和 active mixed-overlay 数据已经删除，不再是 OoO 核的生成或验收输入。
