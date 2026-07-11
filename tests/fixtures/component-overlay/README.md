# Component overlay identity fixture

`alu.v` 是 `a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/alu.v` 的字节级副本，只用于证明 component replacement overlay 不改变 locked 22-file DUT 集合。它不是新的 ALU 手写真源，也不构成 ALU 重构或等价性 claim。

该历史 RTL 来自本仓库 `d22c13c` 引入的 openLA500 baseline。这里随 `alu.v` 提供锁定上游的 MulanPSL-2.0 许可证全文，来源可复核为：

- chiplab `IP/myCPU` commit：`aa3bde1f3e720e71c2c78d6b81930d797b810149`
- 文件：`LICENSE`
- Git blob：`ee5839968a2bf86c93283efc09d40fd050b7cfa2`
- 上游原始文件 SHA256：`6326ae60dd78c85b1f2f6ff308ef1615ff939323270d838e8ebab20f5de1a8c5`
- 本地规范化副本 SHA256：`89591a592b25a07a294c67c0767bb2b061a60e544d76f4bbc438192882f34e92`

本目录的 `LICENSE` 用于满足该上游 `alu.v` 副本的许可证随附要求；副本仅规范化了 CRLF 行尾和行末空白，条款文字未改动。它不声明或改变本仓库其他文件的许可证。验证 overlay 仍会保留锁定 gitlink 自身的 `LICENSE`。
