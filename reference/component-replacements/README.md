# CPU RTL 发布绑定

`core-top.json` 将唯一提交的 CPU RTL `rtl/mycpu_top.v` 绑定到锁定的官方 `rtl/mycpu_top.v` 目标。新版本必须先通过 `make generate-core` 和 `make publish-check` 更新；不再维护旧 leaf/mixed-overlay replacement 集合。
