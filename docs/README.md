# 文档入口

当前可交接的 CPU 架构、目录职责、接口合同、验证命令和已知限制统一维护在 [`ooo-core.md`](ooo-core.md)。

2026-07-26 的主分支整合依据、旧 `dev` 改动取舍和门禁结果见
[`main-integration-20260726.md`](main-integration-20260726.md)；USB/PS2 的跨仓库功能审计和
修复优先级见 [`usb-ps2-audit.md`](usb-ps2-audit.md)。

`docs/contracts/` 中保留的文件只描述仍被新核复用的独立模块（例如 ALU、CSR、TLB、乘除法和缓存边界）；旧标量流水线阶段合同已经删除。历史验证日志不再作为当前接口说明，当前基线以 `ooo-core.md` 的记录和生成物哈希为准。
