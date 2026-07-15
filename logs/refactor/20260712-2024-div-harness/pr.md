# Draft PR：锁定 openLA500 div 的 E33/E34 周期合同

状态：awaiting_pr / draft_only。分支已推送；不自动创建、标记 ready 或合并。

## 行为合同

锁定 a158aa8:rtl/div.v 的 9 端口和 held-request 协议。E33 是 complete=1 通知窗口，
商已最终但余数仍是历史值；E34 沿后 complete=0 且最终商/余数共同有效。

## 验证

- Vivado 2023.2 doctor：PASS。
- WSL automation：233/233，0 skip。
- Golden differential：40 directed + 4096 random，共 4136/4136。
- E33 quotient/history-r 与 E34 final result 各 4136 次，0 mismatch/skip。
- reset、abort、late-abort、held-high A/B restart 轨迹通过。
- 三个 RTL 变异负控均按预期 mismatch 失败。
- 独立只读 reviewer 的 8 项 finding 已修复并复核关闭。
- Claude 在模型启动前因环境变量缺失不可用，故保持 Draft。

## 影响与非目标

本 PR 不修改活动 CPU RTL，无功能、周期或资源 delta。不声明 Spinal、whole CPU、DiffTest、
性能、Linux 或 FPGA PASS。完整证据在 logs/refactor/20260712-2024-div-harness/。

## 回退

revert 本迭代提交；继续保留并使用原 rtl/div.v。
