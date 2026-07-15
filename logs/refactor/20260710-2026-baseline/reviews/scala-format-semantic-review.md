# Scala Gate 与 Claim 边界最终复审

- 复审日期：2026-07-11
- 复审方式：独立 Codex 只读复审
- Claude 状态：本文不是 Claude 审核，不得据此声明已完成 Claude review
- 绑定提交：`45043bd8a89b0e4dea3911ed609d128252f0319f`
- 主证据：`../evidence/scala-summary.json`
- 主证据 SHA-256：`b85fc7d09bb65fff207710c7fdc002f7968b84890991591680d8801fda285eb1`
- 原始结果目录：`/tmp/nscscc-baseline-final-45043bd/scala-check`

## 1. 复审结论

未发现会推翻本次 Scala gate `4/4 PASS` 的证据完整性问题。summary 绑定 exact HEAD，四项任务均实际执行，源码、依赖缓存、ScalaTest XML、仿真产物和 Verilator policy 均有可核对的哈希或结构化字段。

该结果只支持“当前 4-bit Scala ALU 通过有限本地 smoke，且本次 Scala 构建环境受到约束”。它不支持 golden differential、模块等价、流水集成、chiplab 功能通过或可替换原 Verilog 的声明。

## 2. Exact HEAD 与证据绑定

| 核对项 | 结果 |
|---|---|
| 仓库 HEAD | `45043bd8a89b0e4dea3911ed609d128252f0319f`，与 summary 一致 |
| Scala source fingerprint | `9a9f5c1f1075cff81ea5486720e07166a1abfdcdb5a5ab8692aebff28ff8ea89` |
| source input 数量 | 21：4 个构建/格式配置、16 个 main Scala source、1 个 test Scala source |
| source 稳定性 | source/isolated source 的 before/after 四份 fingerprint 完全一致 |
| 当前源码复算 | 21 个逐文件 SHA-256 无 mismatch，整体 fingerprint 与 summary 一致 |
| gate evaluator | `tools/scala_gate.py`，实际 SHA-256 为 `8e5b695c0c71b6e0d297c82bc44e846b1862e05525eed06e5b0bf33818568978`，与 summary 一致 |
| dependency lock | 426 项，整体 SHA-256 为 `f84701a4773644e383c0c658a264d00f04fcbf5e8d03c358af56569a17eb3a35` |

复审时重新对 `/opt/chiplab-tools/root/scala-cache-sbt1.10.11-spinal1.14.2` 执行 lock 校验，仍得到 426 项和上述整体哈希。summary 的 `dependency_cache_stable=true` 还证明 gate 前后缓存清单一致；这不等于对 Maven 上游内容作独立真实性背书。

## 3. Scala Gate 结果

```text
status=pass
planned=4
executed=4
passed=4
failed=0
skipped=0
```

| Task | 判定 | 直接证据 |
|---|---|---|
| `scalafmtCheckAll` | PASS | return code 0；日志 SHA-256 `d0f963d1eb021804138027cce330afea76ebcb0bef4d5234965fcb815c5201b6` |
| `Compile / compile` | PASS | 隔离 workspace fresh compile 16/16 main source；日志 SHA-256 `cf6c65f4896f5c0db71ead1a74503a85cd81bae80be3f75a51d70f5763d63c6e` |
| `Test / compile` | PASS | 隔离 workspace fresh compile 1/1 test source；日志 SHA-256 `c16ce065fa0f5aa98365b42d134cf5dc6b10d8bc0e2f8ba14bc2371f77046608` |
| `Test / test` | PASS | 1 succeeded；failed/canceled/ignored/pending/aborted 均为 0；日志 SHA-256 `890c57857b6d3364a33aa7de8032384e12b0e3a165a33ab4bf2650a5de1b5c36` |

这里的 fresh 是指 gate 将受检输入复制到不含 `target` 的独立 workspace，再核对实际编译数为 16+1；不是仅凭 SBT 最后一行成功文本推断。

## 4. ALU 测试的真实覆盖边界

`ALUSpec.scala` 只有 1 个 ScalaTest case。源码逐项核对得到：

- 12 个 result vector：`ADD`、`SUB`、`SLT`、`SLTU`、`AND`、`NOR`、`OR`、`XOR`、`SLL`、`SRL`、`SRA`、`LUI`。
- 4 个 flag assertion：两次 `overflow=true`、一次 `cmpSub=true`、一次 `overflow=false`。
- 仿真 seed 为 `0x5a17`（23063），但输入向量是固定定向值；该 seed 不能支持“随机 ALU 测试”声明。
- oracle 是测试源码中手写 expected value；测试未同时实例化或调用 `a158aa8` Verilog oracle。

因此，本项是 local directed smoke，不是 golden differential。它没有证明 opcode 编码与 golden 一致，也没有证明未覆盖操作、随机输入、时序/反压、formal、流水集成或 chiplab 行为。

## 5. 运行时隔离与清理

ScalaTest XML SHA-256 为 `313bffb23d0b867af2ab6ccb531ff70a5ddf3dbe9047792e29e359e940ac3c7a`。XML 直接记录：

```text
user.home=/tmp/nsg-be7205faaf01/home
java.io.tmpdir=/tmp/nsg-be7205faaf01/tmp
jna.tmpdir=/tmp/nsg-be7205faaf01/jna
jnidispatch.path=/tmp/nsg-be7205faaf01/jna/jna2919997571988409307.tmp
```

这些路径均在本次隔离 runtime workspace 内，`test_runtime_isolation.passed=true`。复审时 `/tmp/nsg-be7205faaf01` 已不存在，与 `runtime_workspace_cleaned=true` 一致。该证据证明本次 JVM/JNA 运行路径和清理结果，不证明宿主机不存在其他无关进程或缓存。

## 6. Verilator Policy

本次 policy 对生成的 `verilatorScript.sh` 及其引用闭包检查通过：

- `-Wall` 存在；`WIDTH`、`UNOPTFLAT`、`CMPCONST`、`UNSIGNED` 的最终有效状态均为 `Wwarn`。
- 未发现禁止类最终 `-Wno-*`、`-f/-F/@` response file、`.vlt`、inline waiver、缺失 RTL、缺失 include 或无法静态解析的 include。
- 实际扫描的 RTL 输入仅为本次 ALU smoke 生成的 `ALU.v` 与 `ALUSimTop.v`。
- Verilator 为锁定的 `5.020`；summary 同时记录 executable、engine、runtime 和 include tree 的哈希。

这只证明本次 ALU 仿真命令闭包符合当前 policy。它不是全仓 `rtl-static`、Yosys hierarchy/check 或 chiplab overlay RTL 的 lint 结论。

## 7. Claim 判定

| 拟声明 | 判定 |
|---|---|
| exact `45043bd` 的 Scala gate 为 `4/4 PASS`、无 skip | `accepted` |
| 16 个 main 和 1 个 test source 在隔离 workspace 中 fresh compile | `accepted` |
| 426 项锁定依赖、运行时隔离/清理、本次 Verilator policy 有结构化证据 | `accepted` |
| 当前 4-bit Scala ALU 通过 12 个定向结果向量和 4 个 flag 断言 | `accepted_with_qualification` |
| 已完成 `a158aa8` ALU golden differential 或可替换 golden | `unsupported` |
| 已达到 `unit_diff`、`differential_pass` 或 `integrated_pass` | `unsupported` |
| 已通过随机、formal、全仓 RTL static 或 chiplab 集成 | `unsupported` |
| 本结果经过 Claude 审核 | `unsupported` |

最终允许的最宽表述为：在 exact HEAD `45043bd8a89b0e4dea3911ed609d128252f0319f` 上，锁定依赖和隔离运行环境下的 Scala gate 为 `4/4 PASS`；其中唯一测试是当前 4-bit Scala ALU 的 12 个定向结果向量与 4 个 flag 断言的本地 smoke，尚未建立 golden differential 或集成等价证据。
