# 实验与 Claim 证据审计

- 外部审计模型：unavailable
- 本地结构化检查：PASS (20/20)
- 独立只读代码审核：PASS after fixes
- 总体结论：WARN，因为 Claude 未启动；不是 harness 功能失败。

## 检查

- Ground truth provenance：固定 Git blob，SHA-1/SHA256/size 均由 contract gate 复核。
- Oracle：期望商余数由独立 C++ 数学模型计算；DUT 只提供 observed output。
- Result existence：contract、golden differential、doctor 与 automation log 均存在并有 SHA256。
- Number match：4136 transactions、E33/E34 各 4136、reset 54、abort 16、div0 18 与原始 JSON 一致。
- Negative control：三项变异都先成功编译，再以各自预期 mismatch/returncode 1 失败。
- Failure accounting：candidate 失败与 golden stability 失败路径的计数算术有自动化测试。
- Scope：仅为 leaf golden harness；没有 whole-CPU、Spinal、功能、性能、Linux 或 FPGA 数据。

机器检查见 ../evidence/claim-audit.json。外部模型未运行，不能把本文件标成跨模型审计。
