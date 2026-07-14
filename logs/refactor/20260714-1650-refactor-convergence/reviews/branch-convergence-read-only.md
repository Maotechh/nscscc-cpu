# 分支收敛独立只读审核

审核者：子代理 `branch_convergence_map`。本文件不是 Claude 审核。

- 多数关键分支已是 `ce50a05` 祖先。
- 剩余非祖先分支是早期平行 feature heads；其 Scala 核心实现已与当前 tree 相同，或被当前线的
  CACOP、DiffTest、forwarding、active backend 修复取代。
- 不应把旧 branch tree 普通 merge/cherry-pick 回来；若维护者要求收敛历史，只能使用不改变
  当前 tree 的 ours/归档方式。
- 旧 AXI 分支已被旧 ICache 分支覆盖；旧多 replacement overlay 已由单一活动
  `mycpu_top.v` overlay 取代。

结论：支持 history-only 收敛，不支持恢复旧内容。
