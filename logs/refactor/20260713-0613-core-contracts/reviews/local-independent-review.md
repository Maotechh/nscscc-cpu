# 独立只读审核与处置

初审发现：golden 位序 oracle 同源、Commit 缺 counter/CSR read、load/store valid 语义重复、barrier status 缺失、访存地址 load-only 命名、四配置未真实 elaboration、硬件 redirect mux 未测、Commit probe 被裁剪、CoreConfig 缺活动 feature/debug、simWorkspace 污染。全部逐项修复。

复审又发现两个 blocking：CACOP response 语义未写明，以及 pack/unpack 成对交换仍可逃过 roundtrip。前者改为 PRELD/CACOP 均为 one-way；后者新增由 verified `LegacyLayout` 驱动的逐字段 unpack slice 与 oracle pack 比较。新增测试首轮 Test/compile RED，修复 API 后 locked Scala gate 再次 4/4 PASS。

审核支持的 claim 仅为：公共 typed contracts 已建立，golden 位序、方向、宽度和四项合同配置通过机器门禁。审核不支持任何流水、CSR、cache、DiffTest 整机、func/perf/Linux/FPGA 完成 claim。
