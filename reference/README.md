# Reference 数据

本目录保存可复现生成和官方兼容检查需要的锁定数据：

* `manifest.lock`：上游 commit、工具版本和外部环境锁。
* `core-top.ports.json`：官方 `core_top` 的 49 端口及 `TLBNUM=32` 合同。
* `golden-rtl-files.lock`：历史 golden RTL 来源 allowlist，仅供独立 leaf differential gate 使用。
* `scala-dependencies.lock.json`：Scala/SBT 依赖内容锁。
* `component-contracts/`：仍保留的 ALU、cache、mul/div 等独立 leaf 合同。
* `component-replacements/core-top.json`：生成顶层的替换哈希；逻辑目标为 `rtl/mycpu_top.v`，实际文件由 `make generate-core` 生成且不加入 Git。

旧标量流水线的 payload layout、stage contract 和 active mixed-overlay 数据已经删除，不再是 OoO 核的生成或验收输入。
