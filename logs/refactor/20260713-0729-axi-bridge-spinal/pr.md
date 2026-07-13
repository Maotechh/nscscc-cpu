# Draft: migrate active AXI bridge to SpinalHDL

状态：`awaiting_push`，仅允许 Draft PR；首次 GitHub push 因 443 连接失败。代理不创建或合并 PR。

## 行为合同

见 `docs/contracts/axi-bridge.md`。本 PR 只替换活动 `axi_bridge`，不修改 cache、流水线或官方 AXI 接口。

## 验证、风险与回退

本地 contract/Scala/static 和 8192 拍 cycle differential 通过；三项 oracle 负控均检出。官方 locked/mixed `func_lab19` 均在既有 PC `0x1c07c79c` 失败，且 warning/identity gate 失败，因此不得标记 Ready。

回退方式是 revert 本 PR，并恢复 golden `rtl/axi_bridge.v` overlay。Claude review 不可用，PR 在独立审核补齐前保持 Draft。
