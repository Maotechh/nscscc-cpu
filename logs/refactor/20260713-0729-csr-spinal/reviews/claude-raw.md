# Claude 原始调用结果

本迭代实际调用 `claude-review` bridge，关闭 reviewer tools，并在 prompt 中提供 base/head SHA、组件 gate、overlay/smoke 结果及窄 claim。

```json
{"jobId":"34823ce9b6b14baea3a28c1beb6c6389","status":"queued","done":false,"threadId":null,"response":null,"model":null,"provider":null,"error":null,"createdAt":"2026-07-13T06:09:41Z"}
```

```json
{"jobId":"34823ce9b6b14baea3a28c1beb6c6389","status":"failed","done":true,"threadId":null,"response":null,"model":null,"provider":null,"error":"Required provider environment variable is not set: GEEKPIE_CLAUDE_API_KEY","startedAt":"2026-07-13T06:09:41Z","completedAt":"2026-07-13T06:09:41Z"}
```

请求在模型启动前失败，没有 Claude 正文；因此只使用本地只读复核，PR 保持 draft。
