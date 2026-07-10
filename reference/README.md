# Reference 说明

本目录只保存版本锁、来源清单、依赖哈希和小型 manifest，不保存 chiplab、Linux、工具链、波形或生成工程。

- 官方 chiplab reference 必须位于仓库外的 Linux 文件系统，或位于被忽略的 `.work/`。
- 每次验证只使用 `manifest.lock` 的固定 commit，并在独立副本中 overlay DUT。
- `golden-rtl-files.lock` 是 candidate 导出的显式 allowlist；它不是完整功能通过证明。
- `scala-dependencies.lock.json` 锁定专用 SBT boot/Coursier 缓存内全部 JAR、POM、XML 和 properties。缓存位于仓库外，默认目录由 `manifest.lock` 的 `scala_cache_dir` 指定。
- `make scala-cache-bootstrap` 只用于显式 bootstrap/update-lock PR。它拒绝复用或删除已有缓存目录，并会联网解析依赖；普通 `make scala-check` 必须离线运行且不得更新 lock。
- openLA500/chiplab 来源使用木兰宽松许可证第 2 版。引入参考源码时必须保留原许可证和版权声明。
- `a158aa8` 只是 golden candidate。在固定官方环境中通过所需 gate 前不得称为 golden truth。
