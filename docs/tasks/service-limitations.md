# Service Layer Limitations Log

## AG-066
- Enqueue failure compensation currently covers `chat_jobs` path in `ChatService.send_user_message`; analogous compensation paths for other services are handled by their own tasks.
- Compensation records `QUEUE_UNAVAILABLE` and upstream enqueue exception text; finer-grained broker diagnostics (e.g. retry class, transport metadata) are not yet modeled.
- No retry is performed in service layer when enqueue fails; behavior is fail-fast with persisted failed placeholders and task row.
- User placeholder semantics remain asymmetric by design: `user` message keeps `delivery_status=null`, while assistant placeholder and `chat_jobs` row transition to `failed`.

## AG-067
- Multipart validation is represented at service boundary as non-empty `storage_path` + `filename` + required `term_id`; actual raw multipart parsing stays in API layer tasks.
- Validation currently checks presence/non-empty only; MIME/type/size constraints are intentionally deferred to later document pipeline/storage tasks.

## AG-060 / AG-061
- `MilestoneService` currently enforces teacher visibility via active `assignments` relationship only; richer advisor-role mapping (if introduced later) is not yet integrated.
- Milestone date validation only checks ISO format and not cross-field chronology (`start_date <= end_date`) because contract does not enforce it.

## AG-068 / AG-069 / AG-070
- `DocumentService` now persists `document_tasks` and enqueues `pdf_parse`; downstream `document_jobs` fan-out remains delegated to worker/runtime tasks per ADR.
- Storage writes use `adapter.storage.put_bytes` when `file_bytes` is provided; API-layer multipart parsing/storage key naming policy is still deferred to API tasks.
- Enqueue failure compensation marks `document_tasks` as `failed` with `QUEUE_UNAVAILABLE`; no service-layer retry/backoff is performed.
- Service no longer provides a non-app-context enqueue fallback; calling `DocumentService` now requires normal Flask app context and repository-backed dependencies.

## AG-071 / AG-072 / AG-073 / AG-074
- `TopicService` uses synchronous Jieba tokenization to update portrait keywords, but does not yet persist per-token provenance/weights.
- `keyword_jobs` enqueue is triggered from create/update text mutations; de-duplication of semantically equivalent snapshots is not yet implemented.
- Review flow currently models `approve/reject` transitions only; comment persistence/audit trail fields are deferred.

## AG-075a / AG-075b / AG-075c / AG-075d / AG-076 / AG-077 / AG-078
- Selection window gating is term-level and timestamp-based; timezone/holiday policy exceptions are not modeled.
- Application priority conflicts rely on DB unique constraints and fail-fast handling; no automatic priority swap algorithm is implemented.
- `accept` path enqueues `reconcile_jobs` after commit; if enqueue fails, accepted assignment remains committed and failure is downgraded to warning log (no synchronous rollback/retry).
- Service no longer provides a non-app-context enqueue fallback; `teacher_accept_application` executes on normal app-context transaction path only.
- Reconcile enqueue failures are now persisted in `reconcile_dispatch_failures` for offline compensation, but retry/repair still depends on follow-up worker/ops tooling.

## AG-079 / AG-080
- Recommendation scoring is an in-memory keyword overlap baseline over existing topic/profile fields, without offline feature weights or collaborative filtering.
- `explain` currently returns deterministic matched-keyword reasons; richer explanation templates and confidence calibration are not yet implemented.

## AG-081（后续可补充）
- `pdf_parse` 成功写回仅 `result_json.pdf_parse_outline`（页数、`max_chunks`、各页字符数）；**未**持久化分块全文或独立中间文件 URI。若要让 `document_jobs` 少重复读盘或支持断点，需在契约/ADR 中约定中间产物形状与读写方。
- `enqueue_document_jobs` 仍无 `PolicyGateway.assert_can_enqueue` 包装（与 `enqueue_reconcile_jobs` 不同）；若要对文献队列做统一配额/封禁，需扩展 `queue.py` / 契约并补测试。
- 解析成功后按 `expand_default_document_job_plan` **一次性**入队全部 `document_jobs`；高页数 PDF 下的队列峰值未做按波次（如结合 `chunk_summarize_waves`）的延迟入队或限流。
