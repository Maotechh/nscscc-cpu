# Draft PR: IF stage typed migration

状态：`awaiting_push`；本迭代不自动创建或合并 PR。

本变更将活动 IF leaf 重构为 typed `FetchStage` 与显式同步 `LegacyIfStage` 壳，保留 golden 的端口、payload、BTB OR 行为和 flush 状态优先级。证据包括锁定工具链下 2/2 可复现生成、Scala/Python 门禁、warning 白名单、Yosys、固定 seed `20260713` 的 2048 周期 golden/candidate lockstep 和负控首错。

本 PR 草稿不声明官方 chiplab、58/81 功能、NEMU random DiffTest、性能、Linux、Vivado、整机等价或完全重构完成。Claude bridge 因缺少 `GEEKPIE_CLAUDE_API_KEY` 未能返回审核，已按契约记录错误并附独立只读审核；等待人工评审后再决定是否建立 PR。
