# claude-review MCP 原始终态

以下事件为 bridge 返回值的原样 JSON；三个 job 均在模型启动前失败，没有 Claude 正文、thread、provider 或 model。

{"jobId":"884950e282464bdaaf2e1e49b061adc1","status":"failed","done":true,"threadId":null,"response":null,"model":null,"provider":null,"backend":null,"responseId":null,"duration_ms":null,"stop_reason":null,"error":"The responses review backend does not allow reviewer tools","createdAt":"2026-07-11T19:39:40Z","startedAt":"2026-07-11T19:39:40Z","completedAt":"2026-07-11T19:39:40Z","updatedAt":"2026-07-11T19:39:40Z"}

{"jobId":"a3054297d7834c969127004b786df9e0","status":"failed","done":true,"threadId":null,"response":null,"model":null,"provider":null,"backend":null,"responseId":null,"duration_ms":null,"stop_reason":null,"error":"Required provider environment variable is not set: GEEKPIE_CLAUDE_API_KEY","createdAt":"2026-07-11T19:44:21Z","startedAt":"2026-07-11T19:44:21Z","completedAt":"2026-07-11T19:44:21Z","updatedAt":"2026-07-11T19:44:21Z"}

{"jobId":"9d2ba22f27944064a2f220d1dde481c9","status":"failed","done":true,"threadId":null,"response":null,"model":null,"provider":null,"backend":null,"responseId":null,"duration_ms":null,"stop_reason":null,"error":"Required provider environment variable is not set: GEEKPIE_CLAUDE_API_KEY","createdAt":"2026-07-11T20:17:02Z","startedAt":"2026-07-11T20:17:02Z","completedAt":"2026-07-11T20:17:02Z","updatedAt":"2026-07-11T20:17:02Z"}
