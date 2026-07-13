# Draft: migrate active AXI bridge to SpinalHDL

状态：`awaiting_push`，仅允许 Draft PR；代理不创建或合并 PR。

## 行为合同

见 `docs/contracts/axi-bridge.md`。本 PR 只替换活动 `axi_bridge`，不修改 cache、流水线或官方 AXI 接口。

## 验证、风险与回退

验证结果完成后从本轮结构化证据生成。回退方式是 revert 本 PR，并恢复 golden `rtl/axi_bridge.v` overlay。
