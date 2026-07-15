# 下一批活动迁移边界审核

- 特权：优先 `csr` exact overlay；TLB 无 reset、CSR 部分无 reset，不能顺手清零。异常优先级和 breakpoint 重复副作用单独验证。
- 存储：优先 `axi_bridge` exact overlay；I read-only、D read/write，保留 data-read 优先、AXI3 WID、四拍 line write 和 write-buffer-empty 时序。
- 流水：采用 typed stage + 临时 exact legacy wrapper，逐级进入旧 `mycpu_top` 活动路径，最终再由 `OpenLa500Pipeline` 直接连接并删除 wrapper。
- 三条线可从本合同提交并行，但不得同时修改同一个公开 contract；baseline 同点失败只能称诊断一致。
