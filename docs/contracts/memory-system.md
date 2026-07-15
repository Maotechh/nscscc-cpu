# Memory system 合同

活动内存系统由 `ExecuteStage` 创建请求，`MemoryStage` 负责地址转换和异常取消，
I/D Cache 负责命中、回填与写回，`OpenLa500AxiBridge` 是外部 AXI3/WID 的事务所有者。

完成 typed contract 接入前，`MemReq/MemRsp`、`LineReq/LineRsp` 仅表示目标边界，不能据此
声明活动路径已经解耦。迁移必须保持每个普通请求恰有一个响应、握手前 payload 稳定、
取消不撤回已拉高的 valid，并通过随机 backpressure、CACOP/PRELD/uncached 和性能门禁。
