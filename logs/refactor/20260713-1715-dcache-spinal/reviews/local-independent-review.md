# 独立只读审核摘要

审核代理对照 `a158aa8:rtl/dcache.v` 逐项检查 Scala 和差分门禁，发现并推动修复：

1. LFSR 拼写错误与 `lookupToLookup` 运算优先级错误。
2. 差分驱动在上升沿后采样 `rd_req`，导致 refill 未执行且 `cache_miss` 不可见。
3. 额外 reset 初始化不符合 golden 对 dirty、uncached/CACOP buffer 的保留行为。
4. dirty writeback 条件遗漏 replacement valid。
5. 初版 SRAM 生成了写拍仍更新读输出的语义；最终使用 `duringWrite=dontRead`，生成 RTL 为写/读互斥的单端口时序块。
6. 初版随机地址空间过大，几乎不产生 hit；最终驱动使用小 working set，并加入 read/write backpressure、refill gap、中途 reset、uncached、CACOP、PRELD 和 cancel 激励。
7. claim 必须限制为固定 seed、12000-cycle、2-state 的有效协议差分；不得外推到整机或官方 gate。

最终本地 gate 未发现新的 blocking issue，但仍缺 strict commit overlay、外部 Claude 审核、官方功能/性能和形式等价。
