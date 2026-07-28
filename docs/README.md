# 文档入口

当前可交接的 CPU 架构、目录职责、接口合同和验证方法统一维护在 [`ooo-core.md`](ooo-core.md)。精确提交、生成 RTL 哈希、完整 SoC 时序、三次真实板测和下一步风险以机器可读的 [`refactor/status.yml`](refactor/status.yml) 为唯一当前状态源。

`docs/contracts/` 只保留当前仍复用的独立 leaf 合同（ALU、乘除法、CSR、地址转换和 LACC）以及活动发布闭包合同。旧标量流水线、旧 cache/AXI 和早期迁移流程合同已经删除；需要追溯时使用 Git 历史和 `logs/refactor/`，不能把它们当作当前接口或基线。迁移工程时只需要 Git 仓库；`.fpgajob`、Vivado 工作目录和远端结果可根据 `status.yml` 中的 commit、包哈希和 Job ID 重建或重新获取。

仓库根目录的 `baseline.txt` 是最初标量核的比赛性能对照，不是当前 RTL 状态。继续 OoO 开发应从 `status.yml` 的 `baseline.rtl_commit` 开始；比较相对最优性能时使用其中的 `performance_reference`，比较相对原始标量核的总加速时才使用 `baseline.txt`。
