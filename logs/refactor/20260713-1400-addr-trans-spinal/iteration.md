# 20260713-1400-addr-trans-spinal

- Status: implementation_in_review
- Branch / Base SHA / Head SHA: `refactor/20260713-1400-addr-trans-spinal` / `9d319136ce20a7bf8547896fb29a58e2f86ce4f4` / `3f10123`
- Owner / Agent: privileged / Codex
- Selected boundary and selection reason: 在 CSR 之后迁移活动 TLB 与地址转换，解除特权、缓存和流水线集成的依赖；两个模块均有锁定 golden RTL 和可执行行为合同。
- Golden reference and locked tool versions: `a158aa8:rtl/tlb_entry.v` SHA256 `a3e3508a0c755375336ba6db392f9038e1d793042fc21b7cd088fde9febcba1f`；`a158aa8:rtl/addr_trans.v` SHA256 `b25c7585ca410363cbbb25e6669687083687fed1a0641a91ff58b7837c371697`；JDK 17.0.19、SBT 1.10.11、Scala 2.13.16、SpinalHDL 1.14.2、Verilator 5.020、Yosys 0.33。
- Behavior contract: `docs/contracts/addr_trans.md`；TLB 搜索键在 fetch 时捕获、下一拍观察，多匹配 index 按位 OR，write 优先于 invalidate，DMW/分页和 CACOP DI 保留 golden 时序。
- Files changed: Spinal TLB/addr_trans/generator、generated replacement RTL、replacement manifests、TLB cycle-diff gate 和 Makefile unit target、合同。
- Attempts and failures: 首次 TLB gate 使用旧生成物哈希并在 directed expectation 处失败；重新生成当前 Scala 产物后修复。直接 addr_trans Verilator `-Wall` 发现单文件子模块 `DECLFILENAME` 和精确遗留端口的未使用位告警；已逐项绑定生成物哈希记录 waiver，不将其声明为零告警。
- Commands and gate results: Python automation 发现 311 项，301 PASS、10 项既有环境 skip、0 FAIL；locked Scala 4/4 PASS；addr_trans 和 tlb_entry 生成各 2/2、字节可复现；addr_trans 51/51 端口及 TLBNUM=32 参数默认值 exact；Yosys hierarchy/proc/check PASS；TLB unit gate 8192 random cycles PASS（8258 cycles、16577 checks、warning_categories=[]、negative control detected）。
- Functional/performance/resource delta: 未运行整机功能、性能、Linux 或 Vivado implementation；官方 `func_lab19` 仍在基线首错 `0x1c07c79c`，不能扩展为整机通过。
- Residual risks: addr_trans 尚缺独立 cycle-diff；仅有 Verilator 2-state，不是 4-state 或形式等价；TLBNUM 锁定 32；未接入活动 core_top。
- Rollback: revert 本迭代提交，继续使用 CSR 分支上的遗留 `rtl/tlb_entry.v`/`rtl/addr_trans.v`。
- PR URL or awaiting state: `git push -u origin refactor/20260713-1400-addr-trans-spinal` 在 52 秒后被 GitHub HTTPS connection reset，保持 awaiting_push；Claude bridge unavailable，PR 保持 draft。
- Next unblocked candidates: addr_trans cycle-diff、I-cache/D-cache、流水线 stage integration。
