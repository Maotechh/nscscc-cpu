# Claude bridge 原始结果

Start：

```json
{"jobId":"b0a97b665ce7495096c5f2e694c7de6a","status":"queued","done":false,"threadId":null,"response":null,"model":null,"provider":null,"backend":null,"responseId":null,"duration_ms":null,"stop_reason":null,"error":null,"createdAt":"2026-07-14T09:29:26Z","startedAt":null,"completedAt":null,"updatedAt":"2026-07-14T09:29:27Z","resumeHint":"Call review_status with this jobId until done=true."}
```

Terminal status：

```json
{"jobId":"b0a97b665ce7495096c5f2e694c7de6a","status":"failed","done":true,"threadId":null,"response":null,"model":null,"provider":null,"backend":null,"responseId":null,"duration_ms":null,"stop_reason":null,"error":"Required provider environment variable is not set: GEEKPIE_CLAUDE_API_KEY","createdAt":"2026-07-14T09:29:26Z","startedAt":"2026-07-14T09:29:27Z","completedAt":"2026-07-14T09:29:27Z","updatedAt":"2026-07-14T09:29:27Z","resumeHint":"Call review_status with this jobId until done=true."}
```

本文件只保存 bridge 返回值，不构成 Claude 审核意见。
