# Draft PR: refactor/20260713-1400-addr-trans-spinal

状态：`awaiting_push`，不自动创建或合并 PR。

本迭代迁移活动 `tlb_entry` 和 `addr_trans`，加入锁定生成、replacement manifest、行为合同和 TLB golden cycle-diff。TLB gate 在 8192 随机尾周期及 directed cases 下通过，负控能检出同时 write/invalidate 错误。

明确未声明：addr_trans 独立 cycle-diff、整机 func58/81、NEMU random DiffTest、性能、U-Boot/Linux、Vivado implementation/timing/bitstream、4-state/formal 等价。Claude bridge 因缺少 `GEEKPIE_CLAUDE_API_KEY` 不可用，见 `reviews/claude-raw.md`。
