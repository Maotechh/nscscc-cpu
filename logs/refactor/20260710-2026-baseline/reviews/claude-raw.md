# claude-review MCP 原始终态

以下事件为 bridge 返回值的原样 JSON；两个 job 均在模型启动前失败，没有 Claude 正文、thread、provider 或 model。

{"jobId":"e4fab9d9580349a69e3602507ba58d48","status":"failed","done":true,"threadId":null,"response":null,"model":null,"provider":null,"backend":null,"responseId":null,"duration_ms":null,"stop_reason":null,"error":"The responses review backend does not allow reviewer tools","createdAt":"2026-07-10T22:01:43Z","startedAt":"2026-07-10T22:01:43Z","completedAt":"2026-07-10T22:01:43Z","updatedAt":"2026-07-10T22:01:43Z"}

{"jobId":"833f3d577d6e4a63b5acff8bae96bf44","status":"failed","done":true,"threadId":null,"response":null,"model":null,"provider":null,"backend":null,"responseId":null,"duration_ms":null,"stop_reason":null,"error":"Required provider environment variable is not set: GEEKPIE_CLAUDE_API_KEY","createdAt":"2026-07-10T22:02:15Z","startedAt":"2026-07-10T22:02:15Z","completedAt":"2026-07-10T22:02:15Z","updatedAt":"2026-07-10T22:02:15Z"}
