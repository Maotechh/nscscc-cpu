# dev 迭代 001：关键字优先回填复核

## 目标与基线

- 开发分支：`dev`，起点 `ab9fd9978deab6b41ff0fe9146a0abe7ed79ce8c`。
- 决定性基线：提交 `a6311892e7d0766ab21affb985a6cda22915231a`，远端任务 `20260716-063206-7dcf56c4`。
- 基线 perf20：20/20 通过，`soc_count` 总和 206,902,887，`cpu_count` 总和 67,538,910。
- 候选：关键字优先回填（critical-word-first，CWF），提交 `939ad8edab1cfa1a88cbc0229fcc9e1327af3db7`。
- 锁定包：`939ad8e-perf20.fpgajob`，SHA-256 `cdf026ca51f926988d6c22f3b873ab5c9ad593ee2c4581dbfec3cdec56d6404a`。

## 复核动机

历史单次任务 `20260716-070528-a79bb831` 的 `soc_count` 总和为 201,979,978，表面上相对基线加速 1.024373 倍；但 `cpu_count` 仅加速 1.000959 倍。更重要的是，测试 2（bubble_sort）和测试 10（stringsearch）出现 `soc_count == cpu_count`，与 100 MHz 系统计数器和约 32.7 MHz CPU 时钟的物理关系不一致。因此不能把历史单样本的 2.44% 改善当作可靠 CPU 收益。

本轮采用保守规则：同一提交、同一实现产物进行三次完整且有效的真实 perf20 烧录，以三次中执行时间最长（性能最低）的一次作为决定性结果。`infra_error` 不计入样本。

## 规则与实现审计

- `jsfa.pdf` 允许自行选择流水线、分支预测和 Cache 等微结构优化；CWF 不改变 SoC 边界或测试环境。
- 候选源代码只修改 SpinalHDL/Scala 与相应测试，`rtl/mycpu_top.v` 由生成器产生，没有引入手写 Verilog。
- ICache 和 DCache 仍分别为 2 路、256 组、16 字节 Cache 行，容量各 8 KiB，满足竞赛要求。
- Vivado、器件、Chiplab 和 myCPU gitlink 均由 `reference/manifest.lock` 与远端包锁定。

## 远端基础设施记录

`clientctl doctor` 的 13 项检查全部通过，维护模式为关闭；Vivado 为 2023.2（build 4029153），器件为 `xc7a200tfbg676-2` / `xc7a200t_0`。

以下尝试均未进入有效样本，原因完全相同：远端编程阶段缺失 `programming-summary.txt`，终态为 `infra_error`。

| 尝试 | 任务 ID | 幂等键 | 包 SHA-256 | 结论 |
|---|---|---|---|---|
| r1 | `20260717-194634-508148a5` | `nscscc-939ad8e-perf20-cwf-dev-revalidation-r1` | `cdf026ca...d6404a` | 基础设施错误，不计样本 |
| r1-retry1 | `20260717-194743-a3a6fd58` | `nscscc-939ad8e-perf20-cwf-dev-revalidation-r1-retry1` | `cdf026ca...d6404a` | 基础设施错误，不计样本 |

同一时间段另一个来源提交的任务 `20260717-194536-fe9fb830` 也以相同的编程证据缺失终止，进一步说明该故障不特定于当前 DUT。

## 当前决定

- 暂不采纳 CWF，也不把历史单次结果记作性能提升。
- 不回退、不修改锁定候选包；等待远端编程链路恢复后继续取得三次有效样本。
- 板卡不可用期间继续完成本地门禁、架构瓶颈分析与下一候选方案，避免空等。
