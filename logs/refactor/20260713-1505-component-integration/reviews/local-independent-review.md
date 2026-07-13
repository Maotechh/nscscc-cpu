# 独立只读审查

结论：`WARN`，拟声明仅得到部分支持，不能提升为 ready。

## 已发现并修复

- `tlb_entry.json` 和 `addr_trans.json` 的 target 缺少 `rtl/` 前缀，且包含 overlay loader 不接受的 `golden_blob` 字段；已改成锁定 golden 路径和严格四字段 schema。
- `make generate TARGET=tlb` 缺失；已增加 TLB 与 AddrTrans 的 reproducible generate/elaborate 入口，并修正旧的 target 错误提示。

## 保持 open

- 没有 unified multi-component replacement spec，也没有 integration head 官方 overlay。
- RegFile、AddrTrans 的统一 port/lint/yosys/unit gate 仍不完整。
- `CoreTopCompat` 仍实例化 legacy BlackBox，未连接本分支的 Spinal 组件。
- 原始 gate artifact 位于本地 `/tmp`，Git 仅保存哈希摘要，尚不是可长期保留的 release evidence。
- Claude bridge 不可用，PR 必须保持 draft。

允许 claim：代码与既有叶子证据在同一分支共存；本次实际重跑的组件 gate 未发现回归。

禁止 claim：官方 overlay、整机功能、58/81、random DiffTest、性能、系统、Vivado 或完全重构通过。
