# 20260712-2024-div-harness

- 状态：draft / differential_pass
- 分支：refactor/20260712-2024-div-harness
- Base SHA：de6e0845660296d2d3e22a447d31d345afce4333
- 实现与审核目标 Head：03c7fb6fec46107ae44183ed3262198641b333bb
- Owner / Agent：Codex
- 目标边界：div_golden_harness

## 动态选择与范围

div 是 a158aa8 活动 core_top 无条件实例化的 execute 叶子，决定 EX stall 与商/余数写回，
此前没有可执行的逐周期合同。该 RTL 自包含、9 端口、无宏与子模块，因此本迭代只建立
fail-closed golden harness，紧随其后直接进入 Spinal 替换；不改 candidate RTL，不做性能优化，
也不把叶子数量当作整机进度。

## Golden 与行为合同

- Golden：a158aa8ab4d49cece1a0fe488d7ac7dc02bd8cf6:rtl/div.v。
- Git blob SHA-1：225827c7d69addd280cb671c17e067a406a9171f。
- SHA256：7e499f4c43c92154d1d4e21be2f269ac140b4f2b2d944677c71f6f4213b66dc6，2642 bytes。
- 精确端口：div_clk/reset/div/div_signed/x/y/s/r/complete。
- E1-E33 连续保持请求与输入；E33 沿后 complete=1、商已最终、余数仍是历史窗口；E34
  沿后 complete=0 且最终 s/r 共同有效。活动 CPU 在 E34 将指令送入 MEM，沿后组合消费
  更新后的 mod_result，因此这里不声称 CPU 存在余数采样 bug。
- 请求在 E33 到 E34 间撤销会同步 abort；持续拉高时 E35 cleanup、E36 才接受下一笔，
  harness 使用不同 A/B 交易证明真正 rearm。

## 文件变化

- docs/contracts/div.md 与 reference/component-contracts/div.json：人类/机器合同。
- tools/div_contract.py、tests/test_div_contract.py：schema、Git blob 与端口 provenance。
- tools/div_diff.py、tests/test_div_diff.py：Verilator cycle runner、独立数学模型与三项负控。
- Makefile：div-contract、div-golden-unit、div-candidate-unit 统一入口。
- lint-waivers.yml：仅对固定 golden blob 登记 3 条逐行 warning；candidate 不继承。

## 已执行门禁

| 门禁 | 结果 | 证据 |
|---|---|---|
| doctor | PASS | evidence/doctor.json；Head 03c7fb6 与 Vivado 2023.2 hash 匹配 |
| automation | PASS | WSL 233/233，0 skip；final5 原始日志有 SHA256 |
| contract/schema/port | PASS | evidence/contract.json；9 端口与 blob SHA1/SHA256/size 匹配 |
| golden cycle | PASS | evidence/golden-diff.json；40 directed + 4096 random = 4136 |
| E33/E34 | PASS | 4136 pulse、4136 quotient/history-r、4136 final result，0 mismatch/skip |
| reset/abort/div0 | PASS | reset 54、abort 16、divide-by-zero 18、late-abort 1 |
| rearm | PASS | held-high cleanup 1、A 到 B restart 1 |
| negative controls | PASS | result、complete timing、E34 remainder 三项变异均预期失败 |
| artifact claim audit | PASS | evidence/claim-audit.json：20/20 与原始 artifact 一致 |
| independent review | PASS after fixes | 8 项 finding 全部关闭；最终无残余 finding |
| Claude review | UNAVAILABLE | job 284b9e8505c044789952d20723a26631 启动前缺少 API key |

## 尝试、失败与审核修复

1. 初次使用 package 形式运行 unittest，因 tests 不是 Python package 失败；改用 discovery，
   未修改测试内容或减少样本。
2. 一次 PowerShell 到 WSL 的日志命令因引号不闭合失败；用同一测试入口正确转义后重跑成功。
3. 第一次 push 遇到连接 reset；随后普通 push 成功，未强推。
4. Claude bridge 在模型启动前失败；首次外部 reviewer 又在读取前返回 provider 403。有效的
   独立只读 Codex reviewer 后续实际读取 diff、证据和测试，并进行多轮复核。
5. Reviewer 指出的 candidate 合同未绑定、E34 remainder 无负控、held-high 不区分 A/B、
   warning waiver 双事实源、失败 counts 失真和驱动元数据过期均已修复。
6. 最后一轮用四个反例验证 interrupted checks：empty、golden-pass-before-next、
   all-four-pass-before-stability、explicit-stability-fail 均满足计数守恒且至少一个失败。
7. Golden 固定产生 WIDTHTRUNC@82 与两条 UNUSEDSIGNAL@85。runner 绑定原 blob hash、
   规则、行号、完整文本和唯一 waiver_id；任一漂移或新增 warning 都失败。
8. WSL 内运行 evidence-check 时，Windows worktree 的 gitdir 指针被 WSL 错误拼接而失败；
   未改写 git 配置，改在原生 Windows 运行同一 validate-iteration 底层入口并通过。

## 功能、性能与资源差异

本迭代不替换 CPU RTL，故功能、周期、Fmax、LUT/FF/BRAM 均无 candidate delta；没有运行
整机 func、性能或 FPGA gate，也不得把 Vivado doctor 解释成综合/实现通过。

## 残余风险与 Claim 边界

- harness 覆盖固定合同下的合法 level-request、reset、abort、rearm 和固定随机集，不是形式证明。
- a158aa8 whole-CPU baseline 仍在 0x1c07c79c 失败，不能由叶子 PASS 推翻。
- 结果仅支持锁定 golden div 与独立模型/周期合同一致；不支持 Spinal candidate、整机、
  DiffTest、性能、U-Boot、Linux 或 FPGA claim。
- Claude 仍不可用，故 PR 必须保持 Draft；独立 Codex 审核没有冒充 Claude。

## 回退、PR 与下一步

回退本迭代提交即可，继续使用原 rtl/div.v。实现 Head 已推送，状态 awaiting_pr；不自动创建、
标记 ready 或合并 PR。下一迭代为 stacked div-spinal，必须复用本合同并保持 Draft，之后
立即推进 core_top 49 端口兼容边界。
