# 本地独立只读复核

- `ExecuteStage` 的 staged valid/ready、flush、除法等待、访存门控和 store mask/data 已由锁定 golden 做 profile 分离的逐拍比较；未发现候选 warning。
- `LegacyExecuteStage` 端口方向、宽度、同步 reset 和 LACC 条件端口由 Yosys manifest 检查；off RTL 不得用于 on profile，已将该错误命令记录为失败尝试并修正。
- 生成器隔离输出与 committed replacement 现使用同一无提交号 RTL SHA256 `839d5932db50baac933205c26765549344147a58ab056a886a374c0d694351aa`；仅 LACC on 生成物留在外部 artifact，不替换默认 off overlay。
- 锁步编译 warning 只来自锁定 golden/ALU/工具/测试台；候选单独 lint 的 warning 数为 0。该分类不等于整个 translation unit 无 warning。
- 阻塞项：golden `lacc_flush` 未驱动，不能推断四态等价；整机仍由 Verilog MEM/CSR/TLB/cache/AXI 驱动；chiplab func_lab19 baseline 已知在 `0x1c07c79c` 失败；Claude bridge 不可用。

结论：允许提交为 `implementation_in_review` 的窄叶子重构，但禁止标记 integrated/full regression/release ready。
