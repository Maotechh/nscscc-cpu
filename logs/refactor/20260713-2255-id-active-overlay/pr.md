# PR 草稿（不自动创建）

标题：`refactor: add Spinal ID stage to active overlay`

范围：仅在 MEM active overlay base 上加入 `rtl/id_stage.v` replacement、reachability 合同、ID gate 入口和状态日志。

验证：reachability 13/13、Scala 4/4、Windows pytest 323 passed（10 项非 Windows 平台排除）、锁定 chiplab doctor、Vivado 2023.2 doctor 已通过；clean diagnostic overlay、官方 smoke 与独立 claim review 待执行，因此保持 draft。

限制：不宣称整机功能、性能、Linux、Vivado 或完全 SpinalHDL 重构。
