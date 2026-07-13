# Draft PR: migrate active D-cache leaf to SpinalHDL

## Scope

把 `a158aa8:rtl/dcache.v` 的 35-port 活动叶子迁移为 SpinalHDL，并提供锁定生成、静态检查和有效协议逐拍差分。本 PR 不修改活动 `core_top` 接线，不包含 MEM stage、AXI bridge 或其他 cache 重构。

## Evidence

- 日志：`logs/refactor/20260713-1715-dcache-spinal/iteration.md`
- Scala/生成：4/4 + 2/2 PASS，可复现 RTL `35f56d5d...`
- 端口/静态：35/35，Verilator/Yosys PASS
- 差分：12000 candidate cycles + 4096 negative-control cycles，16096/16096，0 mismatch
- 官方环境：locked chiplab doctor PASS
- 未执行：官方 func、58/81、random DiffTest、perf20、U-Boot/Linux、Vivado/FPGA

## Risk and rollback

证据只支持固定 seed、2-state、有效协议 payload 的叶子等价；不是形式证明或整机通过。revert 本 PR 即可回退，活动参赛 top 当前未引用该 replacement。

## State

Draft only；等待 push、strict overlay、外部 claim 审核和维护者决定是否创建 PR。禁止自动合并。
