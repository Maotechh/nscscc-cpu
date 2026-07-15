# Claude 审核状态

- 状态：`unavailable`
- 原因：MCP 返回 `Required provider environment variable is not set: GEEKPIE_CLAUDE_API_KEY`，模型未启动。
- 处置：不得把本地审计写成 Claude 通过；PR 保持 draft/awaiting review。
- 本地只读审计：已核对 base/head、golden SHA、生成 RTL SHA、端口数量、gate JSON 和 chiplab diagnostic 状态。
- 未决风险：Mem 的 FPGA 推断资源/读写模式、未初始化四态行为、func baseline 与候选的因果区分需要后续 gate。
