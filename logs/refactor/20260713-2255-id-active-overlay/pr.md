# PR 草稿（不自动创建）

标题：`refactor: add Spinal ID stage to active overlay`

范围：仅在 MEM active overlay base 上加入 `rtl/id_stage.v` replacement、reachability 合同、ID gate 入口和状态日志。

验证：最终 source HEAD 上 reachability 13/13、Scala 4/4、Windows pytest 323 passed（10 项非 Windows 平台排除）、ID difftest 请求 8192 随机周期/实际 8259 总周期、锁定 chiplab doctor、Vivado 2023.2 doctor 已通过。clean diagnostic overlay 接受 13 个 committed replacement，但 `gate_eligible=false`。

官方 `func_lab19` 严格 FAIL（0/1 PASS）：首错 PC `0x1c07c79c`，246 条 DUT warning、373 条官方环境 warning。trace 与锁定 baseline 字节一致，只支持“未观察到更早可见差异”。Claude bridge 缺 key 失败，已降级独立只读审核；PR 必须保持 draft。

回退：revert 本迭代提交，移除 ID active replacement 与对应状态/证据；不改写 base 历史。

限制：不宣称 active integration、官方功能、性能、Linux、Vivado implementation、顺序等价或完全 SpinalHDL 重构。
