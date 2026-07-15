# 本地独立只读审查

两个独立子代理分别审查 Scala/Make/合同与两个 Python gate。初审发现以下阻断项：

- `core-top-contract` 可省略 chiplab 侧检查并仍 PASS。
- top/clock 变更没有把 doctor、func-full、random、fpga 留在 required gate。
- fresh package 与 tracked overlay/spec 没有自动一致性检查。
- OUT_DIR/manifest/ports symlink 与失败摘要写入存在 fail-open。
- isolated Scala snapshot 未强制等于原 source snapshot。
- TLBNUM 正则可能命中注释，Yosys 未检查 backend 参数。
- wrapper-only 静态门禁容易被扩大表述为完整 package lint。

处置：上述问题均已修复或降窄命名；新增 required chiplab、publish-check、raw-path lstat、snapshot equality、comment-safe TLBNUM、Yosys 参数检查、warning/SKIP 负控，并把静态 scope 固定为 `compat-wrapper-only`。`elaborate --runs 1` 是审查基于旧快照的发现，主线程已改为 2并实际通过。

修复后定向测试为 generator 17/17、core_top gate 24/24，全量自动化 296/296。残余风险未消除：legacy backend、func_lab19 baseline failure、完整 package warning、full/random 缺失和 Claude unavailable，因此本轮只能是 draft `wrapped_golden` 候选，不能是 integrated/full regression。
