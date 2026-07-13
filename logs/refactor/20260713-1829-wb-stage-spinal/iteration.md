# 20260713-1829-wb-stage-spinal

- Status: differential_pass（等待活动 overlay 与 PR 审核）
- Branch / Base SHA / Head SHA: `refactor/20260713-1829-wb-stage-spinal` / `a6788aaf36cea5a90512d60194c9e41a5c127860` / `4d03454359c73854ffecf25a529d820b89fa285e`
- Owner / Agent: Codex / root
- Selected boundary and selection reason: 选择活动 WB 边界；它是五级流水最后的架构提交点，可先建立 CommitEvent 和 DiffTest 观察合同，再接入整机。
- Golden reference and locked tool versions: `a158aa8:rtl/wb_stage.v`，golden SHA256 `8a6f6cb282d152e4b43673397b8c00f598e3d116589e5797fb6feaadbc032a09`；SpinalHDL 1.14.2、Scala 2.13.16、sbt 1.10.11、Verilator 5.020、JDK 17。
- Behavior contract: 保持 493-bit 输入、52 个普通端口和 64 个 DIFFTEST 端口；断点保持锁存 payload，flush 优先，CommitEvent 仅释放一次；异常、CSR/TLB、LL/SC、性能和 debug 输出来自同一锁存状态。
- Files changed: typed `WritebackStage`、legacy `wb_stage` adapter、CommitEvent 观察、Scala 仿真、component contract/spec、gate 脚本和替换 RTL。
- Attempts and failures: 首次 Scala gate 因测试缺少 `-Wall/-Wwarn-*` integrity 失败；补齐后暴露两个 legacy 未使用 payload 位；跨层读取尝试触发 hierarchy violation，已撤回；最后使用测试局部 `-Wno-UNUSEDSIGNAL`，生产 lint 仍执行精确 allowlist。
- Commands and gate results: scalafmt/compile/test-compile/test 4/4 PASS；normal/difftest 端口 52/64 PASS；Verilator lint、Yosys 两 profile PASS；8192 random + directed 共 8238 周期 PASS；负控首错 cycle 3 phase 1。
- Functional/performance/resource delta: 仅局部 WB 重构；未运行整机 func、性能、Vivado，不能据此声明系统功能或资源等价。
- Residual risks: WB 尚未进入活动 `core_top` overlay；官方 func_lab19 基线仍在 `0x1c07c79c` 失败；Claude bridge 因缺少 `GEEKPIE_CLAUDE_API_KEY` 不可用；顺序形式等价尚未证明。
- Rollback: revert 本迭代提交 `4d03454359c73854ffecf25a529d820b89fa285e` 及 gate commit `2cfc0c9d0defefad0da8dcb7ddd775637e8ca47c`。
- PR URL or awaiting state: `awaiting_pr`；已 push 分支，代理不创建或合并 PR。
- Next unblocked candidates: 将 `wb_stage` 加入 active-reachable replacement spec；随后迁移 IF/ID/MEM 中最小可验证边界，并接入 CommitEvent adapter。
