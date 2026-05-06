# Graduation Frontend Design

## Context

The repository currently contains a Flask backend, queue-backed async job flows, contract definitions in `spec/contract.yaml`, and broad backend test coverage. It does not yet contain a dedicated frontend project.

The backend is already strongest in the following product-facing capabilities:

1. Async chat request acceptance and job-state polling.
2. Async PDF upload, parse, and document summary task flow.
3. Supporting domain pages such as topics, taskboard, identity, and terms.

For graduation-project delivery, the frontend does not need to expose every backend capability equally. It needs to support a strong defense/demo story: the user can sign in, interact with the system, observe async processing, and see that the project is more than a static CRUD system.

## Goal

Create a dedicated frontend project under `frontend/` that serves as a graduation-defense-ready product demo.

The frontend should:

- Showcase the strongest backend capabilities first.
- Prioritize visual completeness and demo fluency over total feature coverage.
- Support real API integration for the main demo path.
- Allow secondary modules to be partially integrated if needed.
- Remain isolated from the backend Python project structure.

## Non-Goals

- Building a complete production admin console for every backend domain.
- Refactoring the backend into a full monorepo toolchain.
- Introducing SSR, micro-frontends, or multi-app splitting.
- Implementing every teacher/admin path in this first frontend pass.
- Replacing the current backend contract model.

## Recommendation

Use a standalone frontend project in `frontend/` built with:

- React
- Vite
- TypeScript
- React Router
- Tailwind CSS
- shadcn/ui
- TanStack Query
- Zustand
- Axios

This is the best tradeoff for a graduation-defense build:

- Fast to scaffold and iterate.
- Easy to make visually polished.
- Simple to integrate with the current backend.
- Low risk compared with Next.js or a heavier enterprise stack.

## Product Positioning

The frontend should be framed as an **AI academic assistant workspace**, not as a generic admin system.

That means:

- The home page should emphasize activity, tasks, and outcomes.
- Chat and document workflows should be the primary user story.
- Topics and taskboard should exist as supporting modules that prove system breadth.

The product story for demo purposes is:

1. The user logs in.
2. The user enters a dashboard that summarizes recent work.
3. The user uses async chat and sees job-based completion.
4. The user uploads a PDF and sees document task progression and results.
5. The user can additionally show topic selection and taskboard pages to demonstrate domain coverage.

## Directory Structure

The frontend should be created as a separate project rooted at:

```text
frontend/
```

Recommended repository layout:

```text
app/                 # Flask backend
docs/
spec/
tests/
frontend/            # new React frontend
```

Reasoning:

- Keeps Python and Node.js dependency graphs separate.
- Makes the repository easier to explain in defense.
- Avoids mixing frontend build output with backend source.
- Preserves the current backend project conventions.

## Page Priority

### P0: Main Demo Flow

These pages must be implemented and polished first.

#### `/login`

Responsibilities:

- Accept username and password.
- Authenticate through the backend.
- Persist auth state for subsequent requests.
- Redirect to the application workspace after success.

Demo importance:

- Establishes a real product entry point.
- Makes the rest of the demo feel like a coherent application rather than disconnected pages.

#### `/app/dashboard`

Responsibilities:

- Show current user and current term context.
- Display recent chat jobs and recent document tasks.
- Surface summary cards such as total chats, total document tasks, completed items, and failed items.
- Provide quick entry points into chat, documents, topics, and taskboard.

Demo importance:

- Gives the defense presentation a strong starting page.
- Helps explain the system as a unified workspace.

#### `/app/chat`

Responsibilities:

- Show conversation list.
- Show message stream for the active conversation.
- Allow sending a user message.
- Surface async job states such as `pending`, `running`, `done`, and `failed`.
- Poll chat-job status and update assistant output when complete.

Demo importance:

- This is one of the strongest backend-backed capabilities.
- It directly demonstrates queue-backed async interaction.

#### `/app/documents`

Responsibilities:

- Upload PDF documents.
- Show document task list.
- Show task status, progress, and result summary.
- Allow the user to inspect a single task in more detail.
- Reflect async document processing stages and final result.

Demo importance:

- This is the second strongest backend-backed capability.
- It demonstrates document ingestion, async work, and result visualization.

### P1: Supporting Demo Pages

These pages should be built after the main path is stable.

#### `/app/topics`

Responsibilities:

- Show topic list and topic details.
- Display application or selection-related state where available.
- Emphasize that the system covers graduation topic selection in addition to AI tooling.

This page may be partially integrated if needed.

#### `/app/taskboard`

Responsibilities:

- Show milestone/task-oriented progress.
- Provide a progress-oriented or timeline-oriented view.
- Demonstrate that the system supports structured graduation-process management.

This page may also be partially integrated if needed.

### P2: Optional Or Deferred

- Profile/settings
- Full teacher/admin workflows
- Complex filtering/reporting
- Rich editing capabilities outside the main demo path

## Information Architecture

Recommended route map:

```text
/login
/app
/app/dashboard
/app/chat
/app/documents
/app/topics
/app/taskboard
```

Recommended shell structure:

- Left navigation for primary modules.
- Top bar for user/term context and quick actions.
- Main content panel with page-specific layout.

Recommended navigation order:

1. Dashboard
2. Chat
3. Documents
4. Topics
5. Taskboard

This order reflects demo priority rather than backend domain order.

## UI Style Direction

The UI should feel intentional and presentation-ready rather than generic.

Recommended direction:

- Clean workspace layout.
- Strong visual hierarchy on dashboard cards.
- Light theme first.
- Accent color system that feels academic/productive rather than playful.
- Moderate motion only where it reinforces async state changes.

Visual emphasis should go to:

- Async task status chips.
- Recent activity summaries.
- Chat message flow.
- Document result cards and task progress.

Avoid:

- Plain enterprise table-heavy styling as the dominant feel.
- Overly dark, neon, or futuristic visual treatment.
- Overdesigned landing-page style hero sections inside the app shell.

## Data And State Strategy

### Server State

Use TanStack Query for:

- Authenticated resource loading.
- Conversation lists.
- Chat-job polling.
- Document-task polling.
- Dashboard summaries derived from server resources.

Polling behavior should be explicit:

- Start polling when a chat job or document task is in `pending` or `running`.
- Stop polling when terminal state is reached.
- Surface failure clearly to the user.

### Client State

Use Zustand only for limited app-level concerns:

- Auth/session summary.
- Current user profile summary.
- Current term selection if needed.
- Lightweight UI state that should not live in route-local components.

Do not use Zustand as a replacement for server-state management.

## API Integration Order

### Phase 1: Main Demo Integration

Integrate these first:

- `POST /auth/login`
- `GET /conversations`
- `POST /conversations/{conversation_id}/messages`
- `GET /chat/jobs/{job_id}`
- `POST /document-tasks`
- `GET /document-tasks`
- `GET /document-tasks/{task_id}`

### Phase 2: Supporting Module Integration

Integrate next:

- Topic-related endpoints
- Taskboard-related endpoints

If some supporting endpoints are incomplete or lower value, those pages may use static/demo data temporarily as long as the main path remains real.

## Error Handling

The frontend should consistently surface backend contract errors.

Use one shared API error adapter for:

- `UNAUTHORIZED`
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `QUEUE_UNAVAILABLE`
- `DOMAIN_ERROR`
- Other `ErrorEnvelope` codes defined by the contract

Behavior expectations:

- Form-level validation errors stay near the relevant input.
- Page-level fetch failures show retryable error blocks.
- Async task failures remain visible inside task/message UI instead of silently disappearing.

## Demo Workflow

Recommended defense/demo path:

1. Login.
2. Enter dashboard.
3. Open chat page, send a message, explain async job-state transition.
4. Open documents page, upload a PDF, explain task progress and result display.
5. Briefly show topics page.
6. Briefly show taskboard page.

This sequence keeps the strongest technical story first and uses the supporting modules to broaden scope after the audience is already engaged.

## Vibing Code Workflow

The frontend should be developed in controlled AI-assisted rounds rather than one all-at-once prompt.

### Round 1: Scaffold And Shell

Deliverables:

- `frontend/` project scaffold
- routing
- app shell
- dashboard/chat/documents/topics/taskboard static skeletons

Rules:

- Use static data only
- No real backend integration yet
- Focus on structure and navigation

### Round 2: Visual Completion

Deliverables:

- refined layouts
- dashboard card hierarchy
- polished chat and document page composition
- empty states, loading skeletons, status chips

Rules:

- Keep structure stable
- Improve perceived product quality first

### Round 3: Main API Integration

Deliverables:

- login integration
- chat integration
- document integration
- shared Axios client
- TanStack Query hooks

Rules:

- Only integrate the main demo path
- Do not broaden into secondary modules yet

### Round 4: Async State UX

Deliverables:

- job polling
- task polling
- terminal-state updates in chat/documents/dashboard
- clear failed-state UX

Rules:

- Keep polling bounded and state-driven
- Avoid hidden or implicit refresh behavior

### Round 5: Defense Optimization

Deliverables:

- better microcopy
- stronger homepage summaries
- polished transitions
- consistent error/success feedback
- demo-ready seeded visual states where appropriate

Rules:

- No major architecture changes here
- This phase is for clarity and presentation quality

## Prompting Guidance For AI-Assisted Frontend Work

Each AI prompt should request only one layer of work at a time.

Good prompts:

- scaffold the project and route shell
- improve dashboard/chat/documents UI without API integration
- integrate login/chat/document APIs only
- add polling for async job/task status only
- polish demo states and UX

Bad prompts:

- build the whole frontend from scratch with all pages, all APIs, and final polish

The key rule is:

**one round, one kind of work**

That is the safest way to keep the output coherent and reviewable.

## Risks

### Risk: Overbuilding secondary modules

If topics/taskboard are treated as equal priority with chat/documents, the frontend may become broad but shallow.

Mitigation:

- Lock chat/documents/dashboard as the primary scope.

### Risk: UI polish before structural clarity

If styling begins before layout and route structure are stable, rework cost rises quickly.

Mitigation:

- Keep Round 1 and Round 2 separate.

### Risk: Async behavior feels fake

If polling and terminal-state transitions are not reflected clearly in UI, the strongest backend work will be invisible during defense.

Mitigation:

- Explicitly design for pending/running/done/failed visibility in chat and documents.

### Risk: Frontend and backend terminology drift

If route/component naming diverges from `spec/contract.yaml`, integration and explanation both get harder.

Mitigation:

- Use contract field names and backend resource names directly in API-layer code.

## Final Recommendation

Proceed with a standalone `frontend/` project that presents the system as an AI academic assistant workspace.

The frontend should:

- lead with dashboard, chat, and documents
- support real backend integration for the main demo path
- include topics and taskboard as supporting proof of system breadth
- be developed in staged AI-assisted rounds instead of one-shot generation

This provides the strongest path to a defense-ready frontend without diluting effort into low-value coverage.
