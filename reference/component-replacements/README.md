# CPU RTL 发布绑定

`core-top.json` 将生成的 CPU RTL 哈希绑定到锁定的官方 `rtl/mycpu_top.v` 逻辑目标。`make generate-core` 的权威输出是 `build/core_top/package/rtl/mycpu_top.v`，并创建未追踪的 `rtl/mycpu_top.v` 镜像；新版本必须通过 `make publish-check` 更新并核对哈希。不再维护旧 leaf/mixed-overlay replacement 集合。
