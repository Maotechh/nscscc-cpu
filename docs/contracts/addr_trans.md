# 地址转换行为合同

本合同锁定 `a158aa8:rtl/addr_trans.v`（SHA256 `b25c7585ca410363cbbb25e6669687083687fed1a0641a91ff58b7837c371697`）的活动行为。生成 replacement 由 `OpenLa500AddrTrans.scala` 和内嵌的 `OpenLa500TlbEntry.scala` 提供，公开端口保持原名、方向和宽度。

- `inst_fetch`/`data_fetch` 时分别捕获虚拟地址和 TLB 搜索键；TLB 搜索结果观察为下一拍组合结果。
- `inst_index`/`data_index`/`offset` 使用当前输入地址；DMW 物理 tag 使用已捕获地址，`cacop_op_mode_di` 禁止数据侧 DMW。
- 分页关闭时物理地址等于捕获地址；分页开启时按 DMW0 优先于 DMW1，TLB 大页使用 VPPN[18:9] 和当前页奇偶位。
- TLB fill/write、read、invalidate 的字段映射与 `tlb_entry.v` 一致；同一拍 write 优先于 invalidate。
- 多个匹配项的 index 使用匹配位的按位 OR，不改成优先编码。
- `TLBNUM` 仅保留官方参数合同；锁定比赛配置为 32 项，公开索引宽度仍为 5 位。

该合同只覆盖叶子模块差分，不代表整机流水、异常、缓存或官方 DiffTest 已通过。
