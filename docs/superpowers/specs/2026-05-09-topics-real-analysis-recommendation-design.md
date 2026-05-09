# Topics Real Analysis & Recommendation Frontend Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this spec task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current Topics demo logic with contract-driven teacher analysis and student recommendation flows in `frontend/`, while keeping the existing `/app/topics` workbench layout.

**Architecture:** Reuse the current Topics page as a single workbench with three modes: browse, teacher analysis, and student recommendation. Add a small `users/me` feature layer for the student profile, keep all server state in TanStack Query, and use query-driven polling for topic portrait generation until the async job reaches a terminal state. The page stays visually product-like and does not become a generic admin form.

**Tech Stack:** React, Vite, TypeScript, React Router, TanStack Query, Zustand, Axios, Tailwind CSS, shadcn/ui

---

## Scope

This round only changes the frontend.

In scope:

- `GET /topics` and `GET /topics/{topic_id}` for topic browsing and detail
- `POST /topics` and `PATCH /topics/{topic_id}` for teacher draft save / update
- `GET /users/me` and `PATCH /users/me` for student profile persistence
- `GET /recommendations/topics` for student recommendation results
- async topic portrait polling driven by `llm_keyword_job_status`

Out of scope:

- new backend endpoints
- global layout changes
- dashboard/taskboard refactors
- complicated local state machines beyond what the page needs

## Recommended Approach

1. Keep `/app/topics` as the single entry point.
2. Replace the local mock analysis/recommendation builders with API-backed flows.
3. Let teacher analysis live on the same page as topic drafting and selected-topic portrait viewing.
4. Let student recommendation save the profile first, then fetch recommendations from the backend.

This is the lowest-risk option because it preserves the current navigation and only swaps the data source.

## Alternative Approaches Considered

1. Split teacher analysis into a new route.
   - Cleaner separation, but adds route and navigation overhead with little benefit right now.
2. Split recommendation into its own page.
   - Easier to isolate, but the current workbench already combines teacher/student flow well for demo purposes.
3. Keep one workbench page and wire it to real APIs.
   - Recommended, because it is the smallest change and matches the current product shape.

## File Boundaries

- Modify `frontend/src/pages/topics/topics-page.tsx`
  - Replace mock analysis/recommendation action handlers with real API-backed flow.
  - Keep browse / teacher / student modes.
  - Add teacher save/update and student save/recommend actions.
  - Show async portrait status and recommendation explanations.
- Modify `frontend/src/features/topics/topics.types.ts`
  - Expand DTO/model mapping for the new `portrait` and recommendation explain fields.
  - Keep field names aligned with `contract.yaml`.
- Modify `frontend/src/features/topics/topics.api.ts`
  - Add create/update topic APIs.
  - Add recommendation API wrapper.
- Modify `frontend/src/features/topics/topics.queries.ts`
  - Add query keys and polling-aware topic detail query.
  - Add recommendation query hook if the page fetches results through Query.
- Add `frontend/src/features/users/users.types.ts`
  - Define `UserMe` and `PatchUserMeRequest` mappings for `student_profile`.
- Add `frontend/src/features/users/users.api.ts`
  - Implement `GET /users/me` and `PATCH /users/me`.
- Add `frontend/src/features/users/users.queries.ts`
  - Provide `useUserMeQuery` and `useUpdateUserMeMutation`.
- Modify or retire `frontend/src/features/topics/topics-workbench.ts`
  - Remove mock-only analysis/recommendation builders if they are no longer used.
  - Keep only tiny parsing helpers if the page still needs them.

## Data Flow

### Browse

1. Load the current term from the app store.
2. Fetch `/topics?term_id=...`.
3. When a topic is selected, fetch `/topics/{topic_id}`.
4. Render the topic summary, requirements, keywords, portrait, and job status.

### Teacher Analysis

1. Teacher enters or edits topic content in the workbench form.
2. Submit via `POST /topics` for a new draft or `PATCH /topics/{topic_id}` for an existing one.
3. After save, select the returned topic.
4. Poll the topic detail query while `llm_keyword_job_status` is `pending` or `running`.
5. Stop polling when the status becomes `done` or `failed`.
6. Render the returned portrait fields:
   - `keywords`
   - `difficulty_label`
   - `difficulty_reason`
   - `required_capabilities`
   - `suitable_students`
   - `risks`
   - `summary`

### Student Recommendation

1. Load `/users/me` on page entry or when the student tab opens.
2. Hydrate the form from `student_profile` when present.
3. When the student saves, call `PATCH /users/me`.
4. Fetch `GET /recommendations/topics?term_id=...&top_n=10&explain=true`.
5. Render ranking cards with explain fields:
   - `matched_capabilities`
   - `difficulty_fit`
   - `capacity_status`
   - `warnings`

## Async Polling Rules

- Only poll when a selected topic exists.
- Only poll while the job status is `pending` or `running`.
- Stop immediately on `done` or `failed`.
- Do not keep a stale interval alive after switching topics.
- Use TanStack Query `refetchInterval` rather than manual timers.

## Error Handling

- Keep `ErrorEnvelope` as the only user-facing error adapter.
- Show loading, empty, error, and terminal-state cards separately.
- If a save succeeds but portrait generation is still running, keep the page interactive and show the current job status instead of blocking.

## Testing

Add or update tests for:

- DTO/model mapping for the expanded `portrait` shape
- `users/me` profile mapping
- polling stops at terminal topic job states
- recommendation response mapping and explain fields
- page behavior when topic detail changes after save

## Non-Goals

- No new admin-style table views
- No separate teacher analysis route in this round
- No backend schema changes in this round
- No attempt to make the recommendation engine smarter on the frontend

## Acceptance Criteria

- `/app/topics` still works as a single workbench page
- teacher save/update uses real topic endpoints
- topic portrait rendering comes from backend data, not local mock logic
- student profile persists via `/users/me`
- recommendation results come from `/recommendations/topics`
- polling stops automatically at terminal async states
- the page remains clean, readable, and demo-friendly

