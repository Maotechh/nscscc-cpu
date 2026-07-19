# 4 发射 OoO 重构设计

本文记录 `dev-OoOE` 分支的迁移边界。参考对象是上一级 `ysyx-workbench` 的
`la32r-linux` 分支；它是微结构参考，不是本项目的功能 oracle。功能、异常、CACOP、
DiffTest 和竞赛接口仍以本仓库的 contract 和锁定工具链为准。

## 现状差异

| 项目 | 当前 `SpinalCoreBackend` | ysyx `la32r-linux` | 重构结论 |
| --- | --- | --- | --- |
| 发射/执行 | IF/ID/EX/MEM/WB 单条流水；EX/MEM 只有一个占用寄存器 | `FETCH_WIDTH=4`，`ISSUE_WIDTH=3`，`MACHINE_WIDTH=4` | 前端可取 4 条，rename/dispatch 先做 3 条，执行端口 4 个 |
| 乱序窗口 | 没有 RAT、PRF、ROB、IQ、LSQ | PRF64、ROB32、每端口 IQ8、LDQ/STQ8 | 新后端以 ROB 顺序退休为唯一架构状态出口 |
| 执行端口 | 旧 `ExecuteStage` 由控制字段决定单个 ALU/访存请求 | ALU+CSR、ALU+DIV、ALU+BRU+MUL、LSU | 用 capability 表路由，端口编号不写死在调度器中 |
| 完成 | `WritebackStage` 单路 | `WRITEBACK_WIDTH=5`，广播唤醒并写 PRF | 4 个端口之外保留第 5 条乘法/异步回写通道 |
| 分支 | Decode 阶段比较并触发流水 flush/BTB 修复 | BRU 在执行端口完成，ROB 头部精确恢复 | 分支预测元数据进 Uop，mispredict 只由 ROB 恢复 |
| CSR/TLB | CSR/TLB side effect 分散在流水级 | CSR 端口在 ROB 头部串行化 | CSR/TLB 作为 serial Uop，完成后从 commit adapter 更新 CSR |
| I/D cache | 当前 cache contract 为 16B line | ysyx I/D cache 64B line，L2 2-way/512-set/64B | 新层次固定 64B line，AXI 用 8-beat burst |
| 外部接口 | `CoreTopCompat` 固定 49 端口、单 debug commit | ysyx 内部接口不兼容 chiplab | 保留 compat wrapper；内部 commit 用 3 lane，debug 只观察 lane0 或增加 trace FIFO |

当前基线是约 32.727 MHz、20/20 功能通过；因此不能直接替换顶层，必须每个阶段
保持旧 `CoreTopCompat` 可生成，并让新核拥有独立的 directed/diff-test gate。

## 已建立的结构

`spinal/src/main/scala/openla500/ooo/` 中的结构已经可以独立生成 Verilog：

* `OooCoreConfig`：宽度、ROB/IQ/LSQ/PRF、MSHR、L1/L2 geometry 和执行端口 capability。
* `OooUops`：解码、重命名、完成、恢复和提交 Bundle；ROB pointer 使用完整 flag+index，
  可以拒绝 flush 后的 stale completion。
* `OooRob`：多分配、多完成、3 lane 顺序退休；serial Uop 阻止年轻指令同周期退休，
  但不被误当作 branch recovery。
* `OooRegisterMap`/`OooFreeList`/`OooPhysicalRegisterFile`：speculative RAT、architectural
  RAT、ready table、bitmap free-list 和 WB bypass。
* `OooIssueQueue`/`OooDispatchRouter`：按 capability 选择最老 ready Uop；CSR/serial 只有
  ROB head 可以发射。
* `OooLa32rDecoder`/`OooWideDecode`：从旧 DecodeStage 提取纯组合 LA32R 解码；不复制 GPR
  或标量流水 occupancy。
* `OooExecutionCluster`：ALU/BRU、32-cycle divider、one-cycle multiplier 和 AGU boundary。
  LSU 只交给 LSQ，不直接修改 cache，避免 speculative store 破坏精确异常。
* `OooBackendWithExecution`：rename 到 completion 的独立后端，外部只剩有序 LSQ 和恢复接口。

## 推荐迁移顺序

### 第 1 阶段：先锁定后端协议

1. 用 synthetic Uop 产生 `N` 条独立 ALU、RAW、WAW、branch-mispredict、exception、CSR
   和 flush-after-completion 测试。
2. 检查不变量：`p0=0`、提交顺序等于 program order、旧物理寄存器只在 commit 释放、
   stale ROB pointer 不得写回、异常 lane 后同周期不得再提交年轻指令。
3. 先用 Spinal elaboration gate，再用 Verilator；没有仿真器时不能把“生成成功”称作
   功能通过。

### 第 2 阶段：移植解码和执行语义

1. 将旧 `DecodeStage` 的 bit pattern 和立即数规则搬入 `OooLa32rDecoder`，不要把旧
   `registerFile`、forward stall、BTB 修复状态复制到每个 lane。
2. 端口 0/1/2 先接已验证的 ALU/mul/div；执行结果进入 ROB completion，PRF/IssueQueue
   只消费延后一拍的 WB 广播，切断组合环。
3. CSR read/write、CNT、ERTN、TLB、CACOP、DBAR/IBAR 统一编码成 `systemOperation`，
   只允许 ROB head 发射；提交记录携带 CSR address、mask、write data 和异常 metadata。
4. 分支在执行端比较实际值，completion 带 `actualTaken/target`；ROB 只在该指令成为头部
   时发出 recovery，恢复时清空所有更年轻 RAT/IQ/LSQ 状态。

### 第 3 阶段：LSQ 和内存顺序

1. rename 同时分配 LDQ/STQ index；资源不足时整组 rename backpressure，不能只阻塞 LSU lane。
2. load 保存 ROB/LDQ/STQ 序号。最初版本可以等待所有更老 store 地址确定，正确后再加
   store-to-load forwarding；不要一开始就让 load 绕过未知 store。
3. store 先写 Store Queue/Store Buffer，只有 ROB commit 后才允许 D-cache side effect；
   cache 未接收时必须有 backpressure，不能让 ROB 永远释放仍占用的 store entry。
4. load miss 保存完整 ROB pointer、size/sign-extension 和 destination pdst；响应经过
   MSHR/LSQ 检查后才完成 ROB。flush 后按 ROB pointer 丢弃响应。

### 第 4 阶段：64B L1/L2 和 AXI

1. line address = `{tag,index,6'b0}`；单条 LA32R word 仍按 byte offset 选择，跨 64B line
   的半字/字请求拆成两个 micro-request 或直接产生 ALE，行为要与当前 contract 一致。
2. L1 I/D 各 2-way、64 sets、64B line；每个 miss 建 MSHR，保存 victim、requester ROB/LSQ
   metadata。L2 2-way、512 sets、64B line，统一仲裁 I/D refill/writeback。
3. AXI read burst 为 8 beats x 64-bit（或按现有 SoC 数据宽度换算），`arlen/rlast`、
   write response、backpressure 和 reset 清空必须逐项测试。
4. 先保留当前 cache 的 CACOP/uncached contract，再切换 line storage；禁止以 cache miss
   通过代替完整功能测试。

### 第 5 阶段：前端与顶层切换

1. 从现有 fetch line 取 64B，建立 4-slot instruction buffer；跨 line、branch target、
   exception slot 必须保留 slot order。
2. 每周期最多 decode/rename 3 条，rename 组内做 same-cycle RAW；第 4 个 fetch slot 留在
   buffer，不能静默丢弃。
3. 先在 `CoreTopCompat` 内加入 `backend_select` 的 generator-time 选择，旧核仍可生成；
   新核通过同一 AXI/CSR/debug contract 后才删除 scalar path。
4. 3-lane commit 适配 DiffTest：每周期按 program order 逐 lane 记录，外部单 lane debug
   可以只输出最老 retired lane，但不能用它改变内部 commit。

## 固定宽度实现

当前竞赛实现只支持 `fetch=4`、`decode/rename/dispatch=3`、`execution issue=4`、
`writeback=5`、`commit=3`。四个执行端口允许已在 IQ 中就绪的四条指令同周期发射；前端每拍
最多送入三条新 Uop，ROB 每拍最多顺序提交三条。配置构造器会拒绝其他宽度，避免为了未计划
的 4 提交后端保留验证分支或额外硬件结构。

固定宽度不意味着把端口编号散落在业务逻辑中：FU capability、ROB/FreeList 的三路前缀分配、
五路 completion 和三路 ordered commit 仍各自保持单一职责。这样做是为了让当前 4/3 实现可
维护，而不是承诺未来通过改一个参数就能扩宽。

## 必须避免的短路

* 不能把旧标量流水复制三份再称为 OoO；没有 ROB/RAT/PRF/精确 recovery 就没有乱序退休。
* 不能把 speculative store 直接接 D-cache；这会破坏异常、分支恢复和 store ordering。
* 不能用 `DontCare`、无条件 `0` 或未初始化 Bundle 掩盖 Spinal latch/overlap；当前 gate
  已经捕获过这些问题。
* 不能用局部 directed test 代替 NEMU/DiffTest；尤其是 CSR/TLB/CACOP/LLSC、unaligned 和
  cross-line memory。
* 不能在未确认 WSL、Vivado、Verilator 工具版本和锁定 hash 前开始真实性能结论；WSL 只是
  提高自动化效率，不是设计正确性的前提。
