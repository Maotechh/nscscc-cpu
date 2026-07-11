# 本地独立只读复审

## 范围

- 基准：`322a9e01da06b95b041059cad7c82cdafa881e35`
- 对象：overlay/smoke/identity 的锁、结构化证据发布、物理日志复算和负向测试。
- 身份：独立 Codex 子代理降级复审，不是 Claude 审核。

## 初审发现与处置

1. `accepted/fixed`：release 后按路径撤销 report 存在 TOCTOU。删除该流程，改为 producer 在协作锁内最后写 publication marker；consumer 持同一组锁校验 marker、report SHA、operation、iteration、run id 和 publisher SHA。
2. `accepted/fixed`：裸 PASS JSON 在锁内可见。合同现在明确裸 JSON 不构成证据，缺 marker 或 marker 不匹配均失败；正式 overlay/smoke/identity consumer 已接入 helper。
3. `accepted/fixed`：`release_validation_locks` 只捕获 `Exception`。现改为即使出现 `KeyboardInterrupt/SystemExit` 也尝试全部 lease，再重抛第一个异步异常；有 Windows/WSL 负测。
4. `accepted/fixed`：identity 只捕获部分 stdout 异常和失败路径重新解析 SHA。输出异常不再撤销已发布证据；失败清理只在仍持锁时进行，发布 token 直接由 report 构造。
5. `disputed_with_evidence`：POSIX 同用户恶意进程可绕过锁，在 inode 检查与 unlink 间替换路径。仓库合同的保证对象是遵守 iteration lock 的协作进程；对绕过锁的敌对本地进程不作安全保证。协作进程无法在旧 lock 路径仍存在时创建后继 lock。

## Claim 审核

- publication marker 已进入三条生产路径：`supported`，待 clean commit 重跑正式证据。
- release-all 和部分获取回滚：`supported`，开发态正负测试覆盖。
- 物理 compile/raw/artifact 复算与共同伪造拒绝：`supported`，开发态正负测试覆盖。
- CPU 功能、RTL 等价、性能或正式 chiplab PASS：`unsupported`，本迭代不提出这些 claim。

## 剩余限制

- Claude bridge 不可用，required review 仍为 open blocker。
- 当前结果来自未提交工作树；旧 `322a9e0` exact evidence 已作废。
- 正式 doctor、Scala、rtl-static、locked/mixed overlay、官方 smoke 与 identity 必须在新的 clean commit 上重跑。
- 本轮只构建 Spinal 重构所需验证 harness，不做性能优化。
