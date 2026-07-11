# Claude claim review 请求

- Review target：`45043bd8a89b0e4dea3911ed609d128252f0319f`
- Base：`20cae5fd66391f4a1bccc1b87035be421039144b`
- 分支：`refactor/20260710-2026-baseline-automation`
- 请求时间：`2026-07-11T06:02:15+08:00`

要求 reviewer 严格检查 phantom result、未执行 gate、接口/时序误判、oracle 污染、哈希链断裂与夸大完成度，并逐项评估下列 claim：

1. 本 PR 只建立并加固锁定 baseline 验证闭环。
2. exact 证据证明 `a158aa8` 在单一官方 `func_lab19` 下发生已记录 mismatch，不能成为当前 golden truth。
3. Scala 只可声明构建和有限 ALU local directed smoke，不可声明 golden 等价。
4. Vivado 只可声明 2023.2 安装版本与二进制 probe，不可声明 FPGA flow 完成。
5. 不声明 rtl-static、58/81、random、perf、Linux、资源/Fmax 或完全重构。
6. 下一迭代只应是独立 golden-recovery/cacop PR。

自包含上下文包括 base/head、35 文件和 `8449+/752-` diff 规模、关键源码/测试路径、锁定工具版本，以及 `59/59` 自动化、Scala `4/4`、chiplab doctor `44/44`、22-file overlay、644 warning 和 `func_lab19` 首差的 exact 数字。请求明确说明消息没有伪称附带全部 8449 行 diff；完整 diff 仍须维护者在上述 SHA 间复核。

第一次尝试携带只读工具请求，被 responses backend 在模型启动前拒绝。第二次改用无工具、自包含请求，仍在模型启动前因缺少 `GEEKPIE_CLAUDE_API_KEY` 失败。
