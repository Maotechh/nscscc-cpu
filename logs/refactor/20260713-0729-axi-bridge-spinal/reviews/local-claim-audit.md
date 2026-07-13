# 本地 Claim 与证据一致性审计

本审计由执行代理完成，不具备跨模型或独立 reviewer 身份，只检查文件存在性、数字对应和声明边界。

## 结果

- `C1`：`accepted_with_narrow_scope`。`cycle-diff.json` 实际记录 8192 拍、0 mismatch、相同 trace SHA，且三项 mutation 都被检出；独立审计又以四个额外 seed 各跑 8192 拍，均为 0 mismatch。
- official func：`unsupported_as_pass`。locked/mixed 均为 1 executed / 1 failed / 0 skipped，首错、instruction/cycle、trace 相同；只能称“没有更早选定分岔”。
- identity：`failed`。替换字节和 RTL projection 本来不同，warning 644/641 也不同；不得使用 parser/trace 相同冒充 identity PASS。
- generation：`accepted`。两次输出一致，tracked RTL 的 10819 bytes 与 SHA256 `4c307033...e70a0` 匹配。
- ports/static：`accepted`。65/65 exact；candidate 独立 lint/Yosys 通过。`UNUSEDSIGNAL` 仅对锁定死兼容端口与 `rid[3:1]` 做 scoped waiver，不代表整机 warning PASS。
- reset/period：`accepted_with_finite_scope`。独立审计在空闲、读请求、AW 等待、W 等待和 B 等待附近施加多次同步复位，2048 拍 trace 与 golden 相同；这仍不是全输入序列证明。
- driver masking：`accepted`。AR/AW/W payload 只在对应 valid 为 1 时比较，握手、valid/ready、返回路由和返回数据可观察信号仍逐拍比较；静态测试与源码检查一致。
- overlay provenance：`accepted_for_diagnostic`。locked 为零替换，mixed 仅替换同一 committed Git blob 的 `rtl/axi_bridge.v`，replacement SHA 与报告一致。

## 风险

1. 差分是 Verilator 2-state 固定 seed，不覆盖 4-state invalid payload、所有输入序列或 CDC。
2. driver 仅在 AR/AW/W valid 时比较对应 payload；这是 AXI 可观察合同，不能用于掩盖 valid/ready/return 信号差异。上述信号仍每拍比较。
3. 随机 backpressure 与 directed prefix 是同一次 8192 拍执行，统计中明确不重复计为 16384 拍。
4. golden baseline 本身失败且有 644 条未批准 warning，故 boundary 状态最多为 `differential_pass`，不能提升 `integrated_pass`。
5. 独立多 seed 与复位证据保存在 `evidence/independent-claim-audit.json`；它们扩大了测试覆盖，但不改变上述 release gate 限制。
