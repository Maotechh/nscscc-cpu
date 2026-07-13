# AXI Bridge 独立 Claim 审计

审计者：`/root/axi_audit_finish`（只读、独立于实现代理）。审计对象为提交
`bb2dbff743216e83eeb15f98f0651f717c1b4cc8` 及其本轮证据；未修改实现 RTL。

## 结论

- **非阻塞（本边界）**：65 端口和单模块检查通过；候选 RTL SHA256 为
  `4c307033b1d79da6cc257d314d92ef69830ed87cddc24eb7269ff278927e70a0`。
- **非阻塞（本边界）**：固定 seed `0x1`、`0xdeadbeef`、`0xc001d00d`、`0x7fffffff`
  各运行 8192 拍，golden/candidate trace 均逐拍一致，三项负控均检出。
- **非阻塞（本边界）**：在 0/1/2、40/41、150/151、300/301、500 拍施加同步高有效复位的
  2048 拍轨迹中，golden/candidate SHA256 均为
  `9c3cfc14dac247da439936fd70ad07fb1e9618f17c73616cb903b5204947bb85`。
- **非阻塞（测试合同）**：driver 只在 AR/AW/W 的 valid 为 1 时比较相应 payload；valid、ready、
  RID 路由、返回 valid/last 和其他可观察信号仍逐拍比较。这符合 AXI 的 payload 有效窗口，不能
  被解释为忽略握手差异。
- **非阻塞（来源）**：mixed overlay 只替换同一提交 Git blob 指定的 `rtl/axi_bridge.v`，locked
  overlay 为零替换；replacement spec、SHA256 和 overlay report 互相一致。

## 阻塞项与边界

1. 这些结果仍是有限输入的 Verilator 2-state 仿真，不是全序列/4-state 形式等价，也不是整机功能证明。
2. locked/mixed 官方 `func_lab19` 均在已知 baseline PC `0x1c07c79c` 失败，warning policy 和 identity
   gate 也失败；不能宣称 58/81、随机 DiffTest、性能、Linux 或 Vivado PASS。
3. Claude review MCP 未暴露，且 GitHub push 曾因 443 连接失败；状态必须保持 `Draft`/`awaiting_push`，不自动创建或合并 PR。

机器可读明细见 `evidence/independent-claim-audit.json`。
