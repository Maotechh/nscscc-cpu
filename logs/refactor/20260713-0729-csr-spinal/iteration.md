# 20260713-0729-csr-spinal

- Status: implementation_in_review
- Branch / Base SHA / Head SHA: `refactor/20260713-0729-csr-spinal` / `f621c7a1e056b9f128b86efddbdd2598b3692ecc` / pending
- Owner / Agent: privileged / csr_spinal
- Selected boundary and selection reason: 活动 CSR 同时解除异常、TLB、地址转换和整机 DiffTest 的依赖，且 golden RTL 可独立执行。
- Golden reference and locked tool versions: `a158aa8:rtl/csr.v` blob `8d64a8af6c92b3ea0c35d10ced5e06bd12e574f8`；其余版本见 `reference/manifest.lock`。
- Behavior contract: `docs/contracts/csr.md`
- Files changed: 新增 `OpenLa500Csr`/生成器、CSR 合同、端口/静态/逐拍差分 gate、DIFFTEST replacement 及本迭代证据；更新 Makefile/status/lint waiver。
- Attempts and failures: 首次生成因 golden 保留位的部分赋值检查失败，改为显式自保持且不增加复位值；首次 overlay 前发现缺 `TLBNUM` 参数，生成器补固定兼容参数；初始 CPUCFG 负控未命中读口，补齐 CPUCFG directed read 后在 cycle 59 被检测。
- Commands and gate results: locked Scala 4/4 PASS；Python 307/307 PASS；off/on 生成各 2 次可复现；55/81 exact port PASS；Yosys PASS；Verilator 8 条 legacy waiver 后 PASS；4174 边沿差分 PASS；CPUCFG1 负控按预期 FAIL。
- Functional/performance/resource delta: locked myCPU 单模块 overlay 编译 returncode 0，但整机仍有 145 条未批准 warning，严格集成 gate 为 FAIL；未运行性能或资源测试。
- Residual risks: golden baseline 自身 func_lab19 失败；CSR 单元差分不能替代整机异常/随机 DiffTest。
- Rollback: revert 本迭代提交并恢复 `rtl/csr.v` overlay。
- PR URL or awaiting state: awaiting_push
- Next unblocked candidates: exception/CSR pipeline integration, TLB, address translation
