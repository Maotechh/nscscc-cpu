# 整机 typed contracts 合同

## 事实源

- `a158aa8:rtl/if_stage.v`：FS→DS 109 bit。
- `a158aa8:rtl/id_stage.v`：DS→ES 在 LACC 关闭时 350 bit。
- `a158aa8:rtl/exe_stage.v`：ES→MS 425 bit。
- `a158aa8:rtl/mem_stage.v`：MS→WS 493 bit。
- `a158aa8:rtl/wb_stage.v`：提交、副作用和 exception/ERTN/refetch/icacop/idle flush。
- `a158aa8:rtl/axi_bridge.v`：cache line 与 AXI3/WID 五通道接口。
- 锁定上游 `f89c604:mycpu.h`：LACC operation count 3、operation width 2，因此 LACC-on decode payload 为 353 bit。

`a158aa8` tree 不含 `mycpu.h/csr.h`；宏宽度必须标注来自锁定上游或 locked chiplab header，不能伪称完全由 candidate tree 自证。

## 配置

`CoreConfig` 是 immutable case class，当前只接受已锁定值：XLEN/GPR 32、reset vector `0x1c000000`、legacy reset delay 1、TLB 32、BTB 64、RAS 16、I/D Cache 2 way × 256 set × 16 byte line。整数、mul/div、特权、TLB/DMW、cache/cacop、LL/SC、barrier、preload、BTB 和性能计数是固定启用的活动功能；debug 固定启用。LACC off/on 和 DiffTest off/on 组成四项真实 elaboration matrix，不把其他活动功能伪装成未经验证的可关闭开关。

## 流水

`FetchPayload`、`DecodePayload`、`ExecutePayload`、`MemoryPayload` 和 WB 决策 payload 本身不声明方向，不携带 valid/ready。级间使用 `Stream`；提交使用 `Flow`。固定 packed width 为 109、350/353、425、493，字段 slice 必须由 contract test 对照 golden 位序。

`PipelineCtrl` 保留 exception、ERTN、refetch、icache op、idle、branch repair 和 debug breakpoint 的独立原因。全局 flush 杀死所有年轻指令；branch repair 只杀更年轻 fetch/decode。暂不引入通用 `StageLink`。

`OlderStageOccupancy` 表示 EX/MEM/WB 槽位是否被占用，backpressure 时保持为真，不能从 `fire` 或 ready-qualified valid 推导。历史 `br_to_btb/es_br_pre/ms_br_pre` 统一命名为 `isPredictableBranch`，它表示可由 BTB 维护的分支类别，不表示预测方向。EX/MEM 中的 memory 地址由 load/store 共用；MEM 的 physical/virtual 地址还承担官方 load/store DiffTest 观测，禁止命名为 load-only。

## Memory 与 AXI

CPU 侧 `MemReq/MemRsp`、I-cache 只读 `LineReadPort`、D-cache `LineReadWritePort` 和 AXI3 五通道分层。response 没有 ready 的 golden 端使用 `Flow`；TLB/SC cancel 是独立 sideband，不撤回已握手 payload。`MemoryStatus` 单独提供 DBAR/IBAR 需要的 `writeBufferEmpty/dataCacheEmpty`。PRELD/CACOP 在 request fire 后均不欠 response；普通 load/store 必须恰有一个 response。顶层 AXI 保留 WID 和 8-bit len，不直接暴露 stock Axi4。

活动取指路径在请求接受沿绑定虚拟 set/offset，在下一 lookup 拍绑定地址翻译器输出的物理 tag。
uncached 取指通过一次标量 response 完成；cacheable miss 在四拍 refill 完整组装后只通过一次
128-bit line response 完成，禁止 critical-word 和完整 cache line 对同一请求各产生一次提交。

## Commit 与架构状态

`CommitEvent` 同时表达 normal retire、GPR/CSR、副作用、exception/ERTN、timer、load/store、TLB fill、counter 指令和 CSR read observation。load/store 的 `instructionMask` 是官方 DiffTest 的唯一 8-bit valid 真源，`active` 只由其非零派生。`Flow.valid` 表示 WB 有架构决策；normal retire 由独立 `retired` 字段表示，异常不能被吞掉。`ArchState` 包含 32 GPR 和 locked Difftest CSR state；adapter 不读取流水内部信号。

`CommitGroup(3)` 是同拍退休的固定外部边界：lane 0 最老，lane valid 必须是 prefix，且异常或 ERTN 所在 lane 之后不得再有年轻 lane。`OrderedCommitGroup` 对不合法输入 fail-closed 并报告 contract violation；当前标量 WB 只填 lane 0。Chiplab adapter 为每个 lane 复制 `DifftestInstrCommit`、`DifftestStoreEvent` 和 `DifftestLoadEvent`，异常/ERTN 仍从最老控制 lane 发出，退休计数按同拍有效 lane 数累加。

Golden `wb_stage` 的副作用以 `ws_valid` 驱动，而 breakpoint 会保留该 valid，存在重复 level side effect 风险。WB 行为迁移前必须用 ADR 和 directed test 决定严格复现还是作为独立 bugfix 改成 retire-fire；不得在“等价重构”中静默改变。`CommitEvent` 的长期合同仍是一条架构事件只发一次。

## 完成边界

本迭代只冻结可编译合同和 probe tests，不声明任何 pipeline/CSR/cache 行为已经迁移。合同稳定后 pipeline、privileged、memory、observe owner 可从同一 base 并行；公开字段变化必须先更新本合同和 producer/consumer tests。
