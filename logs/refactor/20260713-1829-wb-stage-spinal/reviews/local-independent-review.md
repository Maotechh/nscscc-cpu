# 独立只读审查

- 代码边界：`WritebackStage` 单独拥有锁存 valid/payload，legacy adapter 只负责端口打包。
- 证据：普通与 DIFFTEST 端口、静态检查和 8238 周期差分均有机器可读结果，负控在 cycle 3/phase 1 首错。
- 风险：生成 RTL 仍不是活动 top；`CommitEvent` 尚未被官方 DiffTest 消费；测试中的 `-Wno-UNUSEDSIGNAL` 只适用于仿真，生产 lint allowlist 必须继续保留。
- 结论：允许提交 draft PR；不得宣称整机功能完成。
