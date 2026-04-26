# Chat And Document Runtime Hardening Design

## Context

This project already has strong layered structure, queue boundaries, and broad test coverage, but four product-level gaps remain:

1. Chat jobs do not complete their persistence loop after worker execution.
2. Document summarization does not actually use extracted PDF content.
3. Multi-chunk document results overwrite each other instead of accumulating.
4. Production deployment still allows known placeholder secrets and does not enforce a real LLM runtime configuration.

The goal of this design is to fix those gaps as a coherent runtime hardening effort instead of patching them one by one.

## Goals

- Make chat delivery product-complete under the existing async queue model.
- Make document processing product-complete from PDF upload to final summary result.
- Replace placeholder runtime behavior with explicit production-safe configuration rules.
- Keep the current domain layering model, but allow contract, schema, and migration changes where needed.
- Preserve asynchronous processing for chat and document jobs.

## Non-Goals

- Adding SSE or WebSocket streaming in this change.
- Rebuilding all queue-backed domains onto a generic orchestration platform.
- Replacing Redis or Postgres.
- Adding multi-provider production support beyond one default OpenAI-compatible implementation and one explicit development mock mode.

## User-Facing Outcome

After this change:

- `POST /api/v1/conversations/{conversation_id}/messages` still accepts a chat request asynchronously, but the job now transitions to a terminal state and the assistant message becomes readable after worker completion.
- `POST /api/v1/document-tasks` still accepts a PDF asynchronously, but document summaries are now derived from extracted page/chunk text, not from metadata-only prompts.
- `GET` endpoints expose clearer task/job progress, error, and completion information.
- Production startup fails fast when secrets or LLM runtime settings are invalid.

## Recommended Approach

### Option A: Complete the current architecture in place

Keep the current `HTTP -> service -> queue -> worker -> use_case -> adapter` model and make its writeback, artifact, and configuration paths real.

Pros:

- Reuses the existing codebase shape and most architecture tests.
- Limits blast radius to the already-identified chat, document, runtime-config, and contract seams.
- Best fit for the current repository maturity.

Cons:

- Requires schema changes and broader contract updates.
- Leaves some queue/runtime duplication across domains for a later cleanup pass.

### Option B: Collapse chat back to synchronous execution

Remove async chat while leaving async document processing in place.

Pros:

- Smaller implementation for chat.

Cons:

- Conflicts with current architecture and queue contract.
- Worse behavior under slow providers, retries, and failure recovery.
- Not recommended.

### Option C: Introduce a generic task runtime for all domains

Create a common execution engine for chat, document, topic, and future async work.

Pros:

- Cleanest long-term model.

Cons:

- Too large for this correction pass.
- Risks turning a runtime hardening task into a platform rewrite.

### Recommendation

Use Option A. It fixes the four real defects without discarding the current architecture investment.

## Architecture Summary

The system remains queue-driven, but moves from "acceptance skeleton" behavior to "terminal state" behavior.

Chat flow:

1. API accepts a user message.
2. Service persists `ChatJob`, user message, and assistant placeholder.
3. Queue enqueues a chat job payload.
4. Worker marks job `running`, builds final messages, calls LLM, persists assistant content, usage metadata, and job terminal state.
5. Polling endpoints expose `pending`, `running`, `done`, or `failed`.

Document flow:

1. API accepts a PDF and creates `DocumentTask`.
2. Storage adapter writes the original PDF.
3. PDF parse worker extracts page text and persists a structured artifact.
4. Document job worker summarizes chunk text from stored artifacts.
5. Aggregate/finalize stages combine chunk summaries into final result artifacts and task-level result fields.
6. Polling endpoints expose progress, stage, errors, and final outputs.

Runtime configuration:

1. Application startup resolves runtime config.
2. Production requires valid secrets, broker configuration, and real LLM provider configuration for LLM-backed features.
3. Development may opt into an explicit mock provider, but mock behavior is never an implicit production fallback.

## Module Boundaries

### `app.adapter.llm`

Responsibilities:

- Define the provider interface used by chat and document summarization.
- Provide one default OpenAI-compatible HTTP implementation.
- Provide one explicit mock implementation for development/test only.

Required changes:

- Stop treating a global empty mock as a safe default runtime.
- Add runtime registration during app startup or runtime initialization.
- Distinguish "LLM not configured" from "LLM returned empty content".

### `app.use_cases.chat_orchestration`

Responsibilities:

- Build the effective message list.
- Execute one chat turn through the configured LLM client.
- Persist worker-side state transitions and response data.

Required changes:

- Replace the current fire-and-forget `llm.complete(messages)` call with a real use case that updates `ChatJob` and `Message`.
- Capture terminal status, provider metadata, and failure information.

### `app.task.chat_jobs`

Responsibilities:

- Validate queue payload shape.
- Call the chat use case.

Required changes:

- Keep business logic out of the task layer.
- Let the use case own state changes and writeback.

### `app.use_cases.document_pdf_parse`

Responsibilities:

- Open the stored PDF.
- Extract page text.
- Persist a structured page-text artifact.
- Plan downstream chunk/aggregate/finalize jobs.

Required changes:

- Stop collapsing parsed output into metadata-only task JSON.
- Save extracted content in a structured artifact model that downstream stages can consume.

### `app.use_cases.document_pipeline`

Responsibilities:

- Read extracted content artifacts.
- Summarize chunks using actual chunk text.
- Persist each chunk summary independently.
- Aggregate chunk summaries into a final result.

Required changes:

- Remove metadata-only prompts.
- Make `aggregate` and `finalize` real stages.
- Stop using flat result patches that overwrite prior chunk output.

### `app.task.document_jobs`

Responsibilities:

- Validate payload shape.
- Advance task status and stage.
- Dispatch to the document use case.

Required changes:

- Preserve stage transitions but move actual summarization logic into use cases.
- Write task status updates without flattening per-chunk outputs into one mutable dictionary.

### `app.document.service`

Responsibilities:

- Accept upload input.
- Validate ownership and term scope.
- Persist the task row and original PDF storage path.
- Enqueue parse work.

Required changes:

- Keep service-level responsibility narrow.
- Expose acceptance-state contract rather than pretending final result fields already exist.

## Data Model Changes

### Chat job state

Retain `chat_jobs` but expand its product meaning.

Required fields:

- `status`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`
- `provider_request_id`
- `model_name`
- `usage_json`

Behavior:

- `pending` means accepted and queued.
- `running` means worker claimed the job.
- `done` means assistant content and metadata were persisted successfully.
- `failed` means the assistant placeholder and job row both reflect terminal failure.

### Messages

Assistant messages remain placeholder-backed, but they are no longer terminally empty.

Required behavior:

- Placeholder assistant row may start with empty `content` and `status=pending`.
- Worker updates it to `running` when execution begins.
- Worker writes final assistant content and `status=done` on success.
- Worker writes failure state and optional failure text or empty content on terminal error.

### Document task state

Retain `document_tasks`, but stop using one flat `result_json` as the source of truth for all intermediate and final output.

Required fields or semantics:

- `status`
- `current_stage`
- `progress_json` or equivalent stage/progress representation
- `error_code`
- `error_message`
- `result_storage_uri` for final durable artifact where relevant
- small task-level summary fields or a compact final result projection

### New `document_artifacts` model

Add a separate artifact table for document pipeline outputs.

Suggested fields:

- `id`
- `document_task_id`
- `artifact_type`
- `stage`
- `chunk_index` nullable
- `storage_uri` nullable
- `payload_json` nullable
- `content_text` nullable
- `created_at`
- `updated_at`

Artifact types required in this change:

- `pdf_pages_text`
- `chunk_summary`
- `aggregate_summary`
- `final_result`

Rules:

- extracted page/chunk text is stored as artifact content, not flattened into task result
- each chunk summary is stored independently
- final result is a separate artifact and optionally projected into the task read model

## API Contract Changes

This change explicitly allows contract updates for correctness.

### Chat endpoints

`POST /api/v1/conversations/{conversation_id}/messages`

- remains `202 Accepted`
- returns `job_id`
- returns user message snapshot
- returns assistant placeholder snapshot
- response is explicitly an acceptance payload, not a completed reply

`GET /api/v1/chat/jobs/{job_id}`

- returns lifecycle metadata:
  - `status`
  - `error_code`
  - `error_message`
  - `user_message_id`
  - `assistant_message_id`
  - `started_at`
  - `finished_at`
  - `model_name`
  - `usage`

`GET /api/v1/conversations/{conversation_id}/messages`

- returns assistant messages whose `content` and `status` reflect worker completion

### Document endpoints

`POST /api/v1/document-tasks`

- remains `202 Accepted`
- returns acceptance-state task payload only

`GET /api/v1/document-tasks/{task_id}`

- returns:
  - task `status`
  - `current_stage`
  - progress metadata
  - task-level summary projection
  - `error_code`
  - `error_message`
  - links or references to final artifacts where needed

Optional addition:

`GET /api/v1/document-tasks/{task_id}/artifacts`

- returns artifact metadata for chunk summaries, aggregate output, and final output
- useful for debugging, frontend inspection, and demo visibility

## State Machines

### Chat job state machine

Valid transitions:

- `pending -> running`
- `running -> done`
- `running -> failed`
- `pending -> failed` only if a claimed job cannot begin execution after dequeue/writeback

Persistence rules:

- worker claim sets `started_at`
- success sets `finished_at`, final assistant content, and usage/provider metadata
- failure sets `finished_at`, `error_code`, `error_message`, and assistant terminal status

### Document task state machine

Top-level transitions:

- `pending -> running`
- `running -> done`
- `running -> failed`

Internal stage model:

- `pdf_extract`
- `chunk_plan`
- `summarize_chunks`
- `aggregate`
- `finalize`

Rules:

- task progress must expose current stage
- chunk completion must accumulate rather than overwrite
- aggregate cannot run before chunk summaries exist
- finalize cannot run before aggregate output exists

## Error Handling

### LLM configuration errors

Rules:

- production cannot silently use mock LLM behavior
- missing provider config must fail startup or make LLM-backed features explicitly unavailable with a configuration error
- an empty model response is a provider result, not a substitute for missing configuration

### Queue failures

Rules:

- acceptance path may still commit task/job rows before enqueue
- enqueue failure must update persisted state to `failed`
- HTTP error mapping stays explicit and consistent

### Worker failures

Rules:

- worker exceptions must become terminal persisted state, not log-only failures
- chat failures update both `chat_jobs` and assistant placeholder state
- document failures update `document_tasks` with failed stage context

### Storage failures

Rules:

- original PDF write failure aborts acceptance
- downstream artifact write failure moves task to `failed`
- artifact reads must remain rooted under allowed storage boundaries

## Security And Runtime Policy

### Secrets

Production validation must reject:

- empty values
- development defaults
- known placeholder values such as `change-me-to-32-bytes-minimum`
- secrets below the minimum acceptable entropy/length threshold

### Compose and env policy

`docker-compose.yml` must:

- read secrets from environment or `.env`
- stop embedding placeholder secrets in committed runtime config

Repository policy:

- commit `.env.example`
- do not commit real runtime secrets

### LLM runtime policy

Production must require:

- provider kind
- base URL where applicable
- API key
- model name
- timeout/retry settings with sane defaults

Development/test may allow:

- explicit mock provider mode

Implicit mock fallback is not allowed outside tests or explicit development configuration.

## Storage Strategy

Use the current local storage abstraction as the default implementation, but keep the artifact model compatible with future object storage.

Rules:

- original PDF stays in file storage
- large extracted text or final exports may live in file storage with references from artifacts
- compact structured metadata may live inline in `payload_json`
- design remains compatible with later replacement by object storage without changing task APIs

## Testing Strategy

### Chat tests

Add or update integration tests to prove:

- chat POST accepts and persists placeholder state
- worker execution transitions job to `done`
- assistant message content is populated after worker run
- failure path transitions job and message to `failed`
- polling endpoint reflects terminal metadata

### Document tests

Add or update integration tests to prove:

- uploaded PDF produces extracted page-text artifact
- summarize stage consumes actual extracted text
- multiple chunk summaries accumulate without overwrite
- aggregate and finalize stages produce terminal output
- task read model reflects progress and final result

### Contract tests

Update OpenAPI examples and schema instances to distinguish:

- acceptance payloads
- in-progress payloads
- terminal success payloads
- terminal failure payloads

### Runtime config tests

Add tests that prove:

- production startup fails for placeholder secrets
- production startup fails for missing LLM configuration when LLM-backed features are enabled
- explicit mock mode remains allowed only in non-production or dedicated test configuration

### Regression tests

Retain existing architecture/layering tests, but add product-closure tests so "all tests green" implies the async flows actually finish and persist usable results.

## Migration Strategy

Apply schema changes via migrations.

Migration requirements:

- preserve existing rows where possible
- backfill nullable metadata fields safely
- initialize new task/job state fields with sensible defaults
- add new artifact table before switching document pipeline reads/writes to it

No destructive backfill assumptions should be made about existing development data.

## Rollout Plan

Suggested implementation order:

1. tighten runtime config and secret validation
2. introduce chat job terminal-state writeback
3. introduce document artifact model and migrations
4. switch PDF parse to persist extracted content artifacts
5. switch summarize/aggregate/finalize stages to real content-driven behavior
6. update API contracts and tests

This order reduces the chance of partial runtime correctness where one path is product-complete and the other is still metadata-only.

## Risks

- Broad contract changes may break tests that currently validate placeholder-only behavior.
- Document artifact storage design can become overcomplicated if it tries to solve every future storage case now.
- Startup validation changes may surface hidden local-environment assumptions.
- Worker writeback logic must avoid double-finishing jobs under retries or repeated dequeue scenarios.

## Risk Mitigations

- Update contract fixtures and integration tests alongside code changes.
- Keep artifact types narrowly scoped to document processing in this pass.
- Make development mock mode explicit rather than implicit.
- Encode valid state transitions in service/use-case logic and test them directly.

## Acceptance Criteria

This design is complete when all of the following are true:

- a chat request transitions from accepted to terminal persisted state after worker execution
- assistant message content is available through the normal read APIs
- a document summary is derived from extracted PDF text, not metadata-only prompts
- multi-chunk document output is accumulated and aggregated without overwrite
- production runtime rejects placeholder secrets and missing real LLM configuration
- updated contracts and tests describe and verify the new behavior
