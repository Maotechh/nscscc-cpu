# Scala 门禁独立审查

> 历史审查快照：本文件保留早期门禁问题与修复过程。`45043bd` final Scala claim 以 `scala-format-semantic-review.md` 为准。

- 审查时间：2026-07-10
- 审查方式：独立 Codex 子代理只读代码审查与实跑
- Claude 状态：未使用；本文件不得表述为 Claude 审核
- 审查范围：`Makefile` 的 Scala/SBT 与 `rtl-smoke` 相关行、`spinal/build.sbt`、`spinal/project/plugins.sbt`、`spinal/.scalafmt.conf`、`spinal/src/test/scala/openla500/ALUSpec.scala`、`tools/scala_gate.py`
- 总结：BLOCKING，当前迭代只能保持 Draft

## 实跑结论

最终复跑命令：

```bash
make scala-check OUT_DIR=/tmp/nscscc-scala-gate-final3 \
  CHIPLAB_TOOL_ROOT=/opt/chiplab-tools/root
```

结果为 `executed=4, passed=3, failed=1, skipped=0`：

- `Compile / compile`：PASS，已启用 `-deprecation -feature -unchecked -Werror`。
- `Test / compile`：PASS。
- `Test / test`：PASS，实际执行 1 个 Verilator ALU directed test，固定 seed 为 `0x5a17`。
- `scalafmtCheckAll`：FAIL，16 个既有 `src/main/scala/openla500/*.scala` 未格式化。

原始结果位于 `/tmp/nscscc-scala-gate-final3/scala-check/`。该目录是临时证据位置，不能作为长期 CI artifact locator。

## Blocking findings

1. **格式门禁尚未通过。** 16 个既有主源码文件不满足新固定的 scalafmt 规则。当前分支不得标记 Ready；本次受限任务没有批量改写这些 CPU 源码。
2. **Verilator 尚未绑定 lock 和本次 artifact。** `ALUSpec` 从 `PATH` 选择 Verilator，runner 没有校验或记录 `verilator_binary_sha256`；SpinalSim workspace 位于 `spinal/target/sim-workspace` 并可复用缓存，可能出现 stale binary PASS。后续必须校验版本/哈希、把 workspace 放进本次 `OUT_DIR`，并禁用或严格绑定缓存 key。
3. **证据没有充分绑定当前源码。** `summary.json` 尚未记录 Git HEAD、manifest 文件 SHA256、build/plugin/scalafmt/test/Scala 源文件哈希。仅记录 manifest 路径和值不足以证明旧报告对应当前工作树。
4. **依赖锁仍不完整。** `sbt-scalafmt=2.5.2`、`scalafmt=3.8.3`、`ScalaTest=3.2.19` 已在构建文件中明确 pin；“未进入 manifest”本身不会选择最新版，但阻塞“全部依赖均由 manifest/解析锁可审计”的 claim。SBT launcher jar 和 resolved dependency 也未记录哈希，SBT 仍可能联网解析固定版本。应由有权修改 manifest/依赖锁的后续变更统一解决。
5. **Spinal warning policy 不完整。** Scala compiler warning 已通过 `-Werror` 收紧，但 ALU elaboration 报告一个 pruned signal warning 后测试仍通过。应单独定义 Spinal elaboration warning 的允许/禁止策略，不能把 Scala `-Werror` 描述为覆盖 Spinal warning。
6. **极端 I/O 错误的计数仍可能失真。** SBT 子进程启动 `OSError` 已被记作实际失败，preflight 失败的 `0/0/0/4` 算术一致且返回非零；但写 task log/summary 时发生 `OSError` 仍可能丢弃已经累积的 task result。后续应逐项原子写 summary，或在 `finally` 中从累积列表结算。

## Claim boundary

当前测试只证明活动 Scala `ALU` 的 4-bit encoded 接口在所列 directed vectors 上符合其当前局部合同，并证明测试实际可编译运行。它不证明：

- 与 `a158aa8` 的 14-bit one-hot `alu.v` 差分等价；
- ANDN/ORN、非法或多 bit op、全部输入空间；
- 流水、异常、commit 或 chiplab 集成正确。

因此不得据此提升 `unit_diff`、`integrated_pass` 或“CPU 正确”状态。

## 已接受并修复

- 添加显式 `status`，失败/skip 均使 gate 非零退出。
- 四个 SBT 子任务独立执行，避免格式失败掩盖 compile/test 结果。
- 测试为 0 时强制失败；当前实际执行 1 个测试。
- 固定 ALU 仿真 seed。
- SBT/Java launcher 二进制校验绑定现有 manifest；Scala/Spinal 版本由 build 读取 manifest。
- SBT 子进程 timeout bytes 与启动 `OSError` 已按失败处理。
- Scala compiler warnings 已设为 fatal；测试中的 structural access 通过显式语言 import 消除 warning。
- `rtl-smoke` 已传递 `CHIPLAB_TOOL_ROOT`。
