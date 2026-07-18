# dev 迭代 002：延迟结果前递

## 状态与基线

- 开发分支：`dev`，工作树基准 `ab9fd9978deab6b41ff0fe9146a0abe7ed79ce8c`。
- 用户对 `AGENTS.md` 的未提交修改始终隔离，本轮未覆盖、暂存或带入评测快照。
- 决定性远端基线：提交 `a6311892e7d0766ab21affb985a6cda22915231a`，任务 `20260716-063206-7dcf56c4`。
- 基线通过 perf20 20/20，`soc_count` 总和 206,902,887，`cpu_count` 总和 67,538,910，CPU 约 32.727 MHz。
- 当前板测状态：有效样本 **0/3**。唯一新尝试在 FPGA programming 阶段发生外部 JTAG 锁占，不能用于功能或性能判断。

## 改进动机

原流水线遇到 EX 级 load/mul/div 产生者时，Decode 中的直接消费者必须等待结果到达 MEM。对非分支、非乘除/加速器消费者，这个气泡可以转换为：消费者先进入 EX，在 EX 中等待并捕获 MEM 的最终结果，再继续执行。

本轮目标是减少常见 load-use 和长延迟结果相关气泡，同时保持精确异常、分支解析与共享乘除单元路径不变。

## 实现

1. `DecodeStage` 增加可配置的 late-result-forwarding 标志和源操作数标记。
2. 仅对完整 CPU 后端启用；Legacy 后端显式关闭，保持旧合同。
3. 分支、乘除法和 LACC 消费者继续使用已验证的 Decode stall 路径，避免将 MEM 结果组合送回共享长延迟单元。
4. `ExecuteStage` 在结果尚未出现时抑制副作用；MEM 结果到达但下游仍背压时，将结果捕获到 payload 寄存器并清除等待标志，避免只持续一拍的 load 结果丢失。
5. 修复了一个被新时序暴露的既有分支问题：Decode 中受 EX 背压的间接分支不得用尚未握手的旧目标驱动 Fetch。`branchRepair.active` 现在与该 Decode payload 的输出 ready 同周期生效；新增单测覆盖“持有期间源寄存器变化、握手时使用新目标”。

开发过程中发现并关闭了三个实质问题：

- 初版形成 MEM→EX→共享乘除结果→MEM 的组合环；通过排除原始操作数消费者消除。
- 初版 dependent load 在 MEM 结果脉冲后可能永久等待；通过 EX 内捕获结果修复。
- CoreMark 首错追踪到受背压 `jirl` 提前发出旧目标 `0x1c009f08`，而实际应为 `0x1c00a798`；通过分支修复握手约束关闭。

## 生成与静态门禁

- 锁定 JDK 17.0.19、Scala 2.13.16、SBT 1.10.11、SpinalHDL 1.14.2。
- 两个独立目录生成的原始 `core_top.v` 完全一致：SHA-256 `d31e30dda0fc87ca554c955d24473c0bf499701e954b49565da4316c7c2d66aa`。
- 经仓库标准 `core_top_gate package` 发布的 `rtl/mycpu_top.v`：SHA-256 `26985409b9e2b6b6d93235d302876534130ac17679d9c89f4e32014cda0527f5`。
- 顶层合同：模块数 1，端口 49（17 input / 32 output），Legacy 后端不可达。
- Scala：19 suites、32 tests 全部通过；包含 late-forward 等待/捕获、异常生产者、乘除消费者和分支背压回归测试。
- Python：391 passed、10 skipped。
- `core-top-contract`、`publish-check`、typed AXI boundary、candidate closure、replacement reachability、port check、严格 Verilator lint 和 Yosys check 全部返回 0。
- `git diff --check` 通过。

## 功能验证

锁定 `func/func_lab19` 镜像 SHA-256 为 `b916b85553da2795d6d80332c40056f960c6c4fd36ae341eb7d8cf494b26281e`，总线随机种子 5,570,815。

- `END by Syscall`
- `Reached test end PC.`
- 无 DiffTest mismatch
- 609,265 周期
- 174,056 条指令
- IPC 0.285682

修复分支握手前后的正确候选在该镜像上周期数完全相同。一次使用 `RUN_C` 测试平台二进制运行功能镜像曾产生异常状态 mismatch；锁回 `RUN_FUNC + TRACE_COMP` 后严格通过，证明该失败是测试平台 profile 污染，未计为 DUT 结果。

## 本地 perf20 结果

原始逐项数据见 `logs/dev/evidence/iteration-002/perf20-fixed-comparison.csv`，候选 20/20 均到达结束 PC 且无 DiffTest error。

| 指标 | 结果 |
|---|---:|
| 胜 / 退化 / 持平 | 15 / 3 / 2 |
| 基线总周期 | 55,098,455 |
| 候选总周期 | 54,590,252 |
| 总周期加速比 | 1.009309409× |
| 算术平均加速比 | 1.013795288× |
| 几何平均加速比 | 1.013551505× |
| 最大收益 | SHA，+7.691638% |
| 最差项 | my_memcmp，-0.045147% |

主要受益项为 SHA（+7.69%）、stream_copy（+5.32%）、fireye_C0（+5.02%）、fireye_I2（+1.91%）。三项退化均小于 0.05%，分别为 fireye_D1、inner_product 和 my_memcmp；在没有真实板卡复测前不把这些微小变化解释为稳定硬件退化。

结果支持“late-result-forwarding 能减少部分相关气泡”，但只支持约 0.93% 的本地总周期改善，不支持 2× 或更高加速主张。

## 最终 Vivado 2023.2

为最终分支修复后字节创建了不移动 `dev` 的评测对象 `c8002ef699446c09ce5d2911ef46946bd048fbb8`，并从本地只读镜像进行标准隔离构建。

| 项目 | 最终值 |
|---|---:|
| Vivado | 2023.2 build 4029153 |
| 器件 | xc7a200tfbg676-2 |
| CPU 时钟 | 32.727 MHz |
| WNS / TNS | +0.008033 ns / 0 ns |
| WHS / THS | +0.052 ns / 0 ns |
| Slice LUT | 22,954 |
| Slice Registers | 23,790 |
| BRAM tiles | 36.5 |
| DSP | 8 |
| no_clock / unconstrained internal endpoints / loops | 0 / 0 / 0 |

实现满足全部用户时序约束并成功生成 bitstream。DRC 为 0 Error、0 Critical Warning；45 条 warning 属于锁定平台既有的 REQP-1840、RTSTAT-10 等类别，标准打包器接受。

最终包：

- 路径：`D:\fpga-agent-client\jobs\iteration-002-c8002ef-perf20.fpgajob`
- SHA-256：`28f916cdc6f60d146caf033c97e89920b8a7373d8bb5373c67525b380f8b4ad0`
- 大小：1,078,881 字节
- manifest 共 9 项；源码、Tcl、XDC、Git 对象等禁止项为 0。
- manifest 锁定 `perf20`、`c8002ef`、chiplab `a2e11b3`、myCPU gitlink `aa3bde1`、Vivado 2023.2 与正确器件。

## 远端真实烧录

队列查询为 0 个活动任务、maintenance=false。新包的第一次尝试如下：

| 尝试 | 任务 ID | 终态 | 有效样本 |
|---|---|---|---|
| r1 | `20260718-022339-4680695d` | `infra_error` | 否 |

服务端 Vivado 日志给出：

```text
ERROR: [Labtoolstcl 44-494] There is no active target available for server at localhost:3121.
Target jsn-JTAG-SMT2-210251A08870 may be locked by another hw_server.
```

该任务没有 `programming-summary.txt`、`board-summary.txt` 或 `perf_vio.csv`，所以没有程序真正烧录/运行的证据，不能计入三次样本。此故障与此前 CWF/旧 late-forward 包一致，且不特定于当前 DUT。评测技能禁止使用管理员凭据或由普通 Agent 切换 maintenance；需要外部释放 JTAG target 后继续。

## 规则审计

- `jsfa.pdf` 允许修改流水线、分支预测和 Cache 微结构；本轮未修改测试环境或评测接口。
- ICache、DCache 仍各为 8 KiB，未低于规则要求。
- 所有 CPU 行为修改均位于 SpinalHDL/Scala；`rtl/mycpu_top.v` 由锁定生成与发布流程机械产生，没有手写 Verilog。
- 未修改 Vivado 版本、器件、时钟约束、测试 bin、VIO 判据或远端服务。
- 评测包内不含源代码或构建脚本。

## 当前决定与下一步

- 当前不提交：本地提升远低于 2×，且缺少三次有效远端样本，不满足 `AGENTS.md` 的性能提交条件。
- 当前不回退：本地 20/20、功能门禁、时序与 bitstream 均通过，且总周期有正收益；保留候选和不可变评测包等待板卡恢复。
- 板卡恢复后对同一包取得三次有效 perf20，取最慢一次作为决定性结果，再决定采纳或回退。
- 板卡阻塞期间可继续只读分析下一候选；优先核查 DCache tag 更新是否存在测试间状态干扰，并继续寻找可独立开关、可 A/B 的 load-use、取指和分支吞吐优化，避免覆盖本轮快照。
