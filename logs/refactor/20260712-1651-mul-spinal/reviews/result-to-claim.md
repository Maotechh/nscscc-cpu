# Result-to-Claim

- Reviewer：`/root/mul_result_claim`
- Review target：`f6c55e6dcb42761c283febf99460214452628fd0`
- Overall：`partial`
- Confidence：`high`

## C1：支持，严格限于 candidate 合同

提交 RTL 可复现、精确匹配六端口；4128/4128 cycle differential 与 3/3 candidate
2-state formal/负控支持“首次 active capture 后满足独立数学和 reset-hold 合同”。
该结论不支持 golden 完整 formal、4-state X/Z、post-synth 或整机等价。

建议措辞：在 `f6c55e6` 上，SpinalHDL 生成的 `mul` 在首次有效采样后的 2-state
语义下，通过独立数学模型的 4128 组周期差分，以及 active-capture/reset-hold 时序归纳证明
和两项负控；这只证明 candidate 满足锁定合同。

## C2：支持，严格限于单项失败诊断

candidate/mixed 在同一 `func_lab19` 中均 FAIL；首错、172552 instructions、602903
cycles 和 trace SHA 相同，mixed 的 DUT warning 从 280 减到 276。只能称截至共同失败点
未观察到差异，不能称功能通过或整机等价。

## C3：不支持

只有一个官方 smoke case 且结果失败。58/81、random、perf、U-Boot/Linux、implementation、
timing 和 bitstream 均没有通过证据。状态必须保持 `implementation_in_review`。
