# Claude 原始响应

## review_start

```json
{"jobId":"c819801d05724dd78cafa059dc58a4b7","status":"queued","done":false,"threadId":null,"response":null,"model":null,"provider":null,"backend":null,"responseId":null,"duration_ms":null,"stop_reason":null,"error":null,"createdAt":"2026-07-12T21:57:41Z","startedAt":null,"completedAt":null,"updatedAt":"2026-07-12T21:57:41Z","resumeHint":"Call review_status with this jobId until done=true."}
```

## review_status

```json
{"jobId":"c819801d05724dd78cafa059dc58a4b7","status":"failed","done":true,"threadId":null,"response":null,"model":null,"provider":null,"backend":null,"responseId":null,"duration_ms":null,"stop_reason":null,"error":"Required provider environment variable is not set: GEEKPIE_CLAUDE_API_KEY","createdAt":"2026-07-12T21:57:41Z","startedAt":"2026-07-12T21:57:41Z","completedAt":"2026-07-12T21:57:41Z","updatedAt":"2026-07-12T21:57:41Z","resumeHint":"Call review_status with this jobId until done=true."}
```

模型未启动，没有 Claude 审核内容。
