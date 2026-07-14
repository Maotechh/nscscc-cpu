# 独立只读成果与 Claim 审查

- 审查目标：`b2a73c83f9d849c6f67828e8dcfdd39a620e00ed`
- 审查方式：独立子代理只读检查代码、机器证据、哈希和拟声明；不是 Claude 审核
- 结论：`open`，迭代必须保持 blocked/draft

## Claim 判定

- C1 `accepted_with_scope`：`cacop-directed.json` 的 10/10、958 候选 lockstep 拍、4790 总仿真拍、零 mismatch 和三组负控均能由 gate 代码与机器字段交叉核对。结果只绑定文件内的两个候选 RTL SHA，因缺少 source HEAD 不能直接绑定到 `b2a73c8`；也不支持完整 cache、整机或形式等价。
- C2 `accepted_with_scope`：clean `b2a73c8` 的 Scala、两次可复现生成、package/publish、49 端口和 Yosys 有机器证据；strict lint 明确 FAIL，不能把静态门禁整体表述为通过。
- C3 `accepted_with_scope`：官方 diagnostic smoke 确实执行 1 项、失败 1 项、skipped 0，首错为 NEMU `0x1c07cfcc` 对 DUT `0x1c07cfdc`。只能称旧首错被越过后出现新首错，不能称功能通过。
- 完整 core/function、58/81、random、perf20、U-Boot、Linux、Vivado release、完整顺序等价：`unsupported`。

## 阻塞问题

1. strict lint 仍因未批准 warning 失败；最终摘要没有保留精确数量。
2. `func_lab19` 在 `0x1c07cfcc` 失败。
3. smoke/overlay 是 mixed diagnostic component replacement，`gate_eligible=false`，不能冒充 locked release candidate。
4. 旧 `/tmp` 和 `build/` external locator 已清理，原始大 artifact 当前不可获取；仓库只保留摘要、哈希和首错。
5. Claude bridge 不可用，不能提升 ready。

## 下一步

建立独立 BTB/branch replay harness，先证明 lookup valid 与重复 commit 的因果关系；修复后重跑同一 official smoke。不要先扩展到性能或系统测试。
