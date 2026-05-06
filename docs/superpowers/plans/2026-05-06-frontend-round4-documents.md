# Frontend Round 4 Documents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `frontend/` 中完成 `/app/documents` 的真实联调，支持 PDF 上传、任务列表、任务详情、状态驱动轮询，以及上传成功后自动选中新任务。

**Architecture:** 延续 Round 3 的前端分层：Zustand 只保留登录态与当前学期，Axios 继续负责鉴权与统一错误透传，Documents 的服务器状态全部由 TanStack Query 管理。页面只维护 `selectedTaskId`、上传表单临时值和轻量错误提示；当前选中任务详情作为轮询真源，列表只做同步刷新而不做高频主轮询。

**Tech Stack:** React 19, Vite 7, TypeScript, React Router, Tailwind CSS v4, shadcn/ui, TanStack Query, Zustand, Axios, Vitest

---

## File Structure

- Modify: `frontend/src/pages/documents/documents-page.tsx`
- Modify: `frontend/src/app/styles.css`
- Create: `frontend/src/features/documents/documents.types.ts`
- Create: `frontend/src/features/documents/documents.utils.ts`
- Create: `frontend/src/features/documents/documents.api.ts`
- Create: `frontend/src/features/documents/documents.queries.ts`
- Create: `frontend/src/features/documents/documents.utils.test.ts`

### Task 1: Add Document Types And Pure Utility Tests

**Files:**
- Create: `frontend/src/features/documents/documents.types.ts`
- Create: `frontend/src/features/documents/documents.utils.ts`
- Create: `frontend/src/features/documents/documents.utils.test.ts`

- [ ] **Step 1: Write the failing utility test**

```ts
// frontend/src/features/documents/documents.utils.test.ts
import { describe, expect, it } from "vitest";

import {
  buildDocumentSummary,
  getDocumentProgressLabel,
  isDocumentTaskTerminal,
  shouldPollDocumentTask,
} from "@/features/documents/documents.utils";
import type { DocumentTask } from "@/features/documents/documents.types";

const baseTask: DocumentTask = {
  id: "task-1",
  term_id: "term-1",
  status: "running",
  filename: "paper.pdf",
  task_type: "summary",
  language: "zh",
  current_stage: "summarize_chunks",
  progress: { completed_chunks: 1, total_chunks: 3 },
  artifacts: [],
  created_at: "2026-05-06T00:00:00Z",
  updated_at: "2026-05-06T00:00:00Z",
  retry_count: 0,
  result: {
    summary: "summary text",
    bullet_points: ["point-a", "point-b"],
    raw_model: "gpt",
  },
};

describe("documents.utils", () => {
  it("treats done and failed as terminal", () => {
    expect(isDocumentTaskTerminal("done")).toBe(true);
    expect(isDocumentTaskTerminal("failed")).toBe(true);
    expect(isDocumentTaskTerminal("pending")).toBe(false);
  });

  it("polls only pending and running tasks", () => {
    expect(shouldPollDocumentTask("pending")).toBe(true);
    expect(shouldPollDocumentTask("running")).toBe(true);
    expect(shouldPollDocumentTask("done")).toBe(false);
  });

  it("formats progress labels from object progress", () => {
    expect(getDocumentProgressLabel(baseTask)).toBe("1 / 3 chunks");
  });

  it("extracts summary and bullet points safely", () => {
    expect(buildDocumentSummary(baseTask)).toEqual({
      summary: "summary text",
      bulletPoints: ["point-a", "point-b"],
    });
  });
});
```

- [ ] **Step 2: Run the utility test to verify it fails**

Run: `npm run test -- --run src/features/documents/documents.utils.test.ts`  
Expected: FAIL with import-not-found errors for `documents.utils` and `documents.types`.

- [ ] **Step 3: Add the document types and utilities**

```ts
// frontend/src/features/documents/documents.types.ts
import type { AsyncStatus } from "@/types/app";

export type DocumentTaskType = "summary" | "conclusions" | "compare";
export type DocumentLanguage = "zh" | "en";

export type DocumentTaskResult = {
  summary?: string;
  bullet_points?: string[];
  raw_model?: string;
} | null;

export type DocumentArtifactRef = {
  id?: string;
  artifact_type?: string;
  stage?: string;
  chunk_index?: number | null;
  storage_uri?: string | null;
  payload?: Record<string, unknown> | null;
};

export type DocumentTaskListItem = {
  id: string;
  term_id: string;
  status: AsyncStatus;
  filename: string;
  current_stage?: string | null;
  progress?: Record<string, unknown>;
  task_type?: DocumentTaskType;
  created_at: string;
  updated_at?: string;
  retry_count?: number | null;
  result_preview?: string | null;
};

export type DocumentTask = {
  id: string;
  term_id: string;
  status: AsyncStatus;
  filename: string;
  task_type: DocumentTaskType;
  language: DocumentLanguage;
  current_stage?: string | null;
  progress?: Record<string, unknown>;
  artifacts: DocumentArtifactRef[];
  locked_at?: string | null;
  last_completed_chunk?: number | null;
  created_at: string;
  updated_at: string;
  result?: DocumentTaskResult;
  result_storage_uri?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  retry_count: number;
  max_attempts?: number | null;
  next_retry_at?: string | null;
};

export type UploadDocumentPayload = {
  file: File;
  termId: string;
  taskType: DocumentTaskType;
  language: DocumentLanguage;
};
```

```ts
// frontend/src/features/documents/documents.utils.ts
import type { AsyncStatus } from "@/types/app";
import type { DocumentTask } from "@/features/documents/documents.types";

export function isDocumentTaskTerminal(status: AsyncStatus) {
  return status === "done" || status === "failed";
}

export function shouldPollDocumentTask(status: AsyncStatus) {
  return status === "pending" || status === "running";
}

export function getDocumentProgressLabel(task: Pick<DocumentTask, "progress">) {
  const completed = task.progress?.completed_chunks;
  const total = task.progress?.total_chunks;

  if (typeof completed === "number" && typeof total === "number") {
    return `${completed} / ${total} chunks`;
  }

  return "处理中";
}

export function buildDocumentSummary(task: Pick<DocumentTask, "result">) {
  return {
    summary: task.result?.summary ?? "",
    bulletPoints: task.result?.bullet_points ?? [],
  };
}
```

- [ ] **Step 4: Run the utility test to verify it passes**

Run: `npm run test -- --run src/features/documents/documents.utils.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/documents.types.ts frontend/src/features/documents/documents.utils.ts frontend/src/features/documents/documents.utils.test.ts
git commit -m "test: add document utility coverage"
```

### Task 2: Build Document API Layer And Query Hooks

**Files:**
- Create: `frontend/src/features/documents/documents.api.ts`
- Create: `frontend/src/features/documents/documents.queries.ts`

- [ ] **Step 1: Add the document HTTP methods**

```ts
// frontend/src/features/documents/documents.api.ts
import { apiClient } from "@/lib/axios";
import type {
  DocumentTask,
  DocumentTaskListItem,
  UploadDocumentPayload,
} from "@/features/documents/documents.types";
import type { PaginatedResponse } from "@/features/chat/chat.types";

export async function getDocumentTasks() {
  const response = await apiClient.get<PaginatedResponse<DocumentTaskListItem>>("/document-tasks", {
    params: {
      page: 1,
      page_size: 50,
    },
  });

  return response.data;
}

export async function getDocumentTask(taskId: string) {
  const response = await apiClient.get<DocumentTask>(`/document-tasks/${taskId}`);
  return response.data;
}

export async function uploadDocumentTask(payload: UploadDocumentPayload) {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("term_id", payload.termId);
  formData.append("task_type", payload.taskType);
  formData.append("language", payload.language);

  const response = await apiClient.post<DocumentTask>("/document-tasks", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}
```

- [ ] **Step 2: Add TanStack Query hooks for list, detail, upload, and polling**

```ts
// frontend/src/features/documents/documents.queries.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getDocumentTask,
  getDocumentTasks,
  uploadDocumentTask,
} from "@/features/documents/documents.api";
import type { DocumentTask, UploadDocumentPayload } from "@/features/documents/documents.types";
import { shouldPollDocumentTask } from "@/features/documents/documents.utils";

export const documentKeys = {
  all: ["documents"] as const,
  list: () => [...documentKeys.all, "list"] as const,
  detail: (taskId: string) => [...documentKeys.all, "detail", taskId] as const,
};

export function useDocumentTasksQuery(enabled: boolean) {
  return useQuery({
    queryKey: documentKeys.list(),
    queryFn: getDocumentTasks,
    enabled,
  });
}

export function useDocumentTaskQuery(taskId: string | null, enabled: boolean) {
  return useQuery<DocumentTask>({
    queryKey: taskId ? documentKeys.detail(taskId) : [...documentKeys.all, "detail", "empty"],
    queryFn: async () => getDocumentTask(taskId!),
    enabled: enabled && Boolean(taskId),
  });
}

export function useUploadDocumentTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UploadDocumentPayload) => uploadDocumentTask(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: documentKeys.list(),
      });
    },
  });
}

export function usePollingDocumentTaskQuery(taskId: string | null, enabled: boolean) {
  const queryClient = useQueryClient();

  return useQuery<DocumentTask>({
    queryKey: taskId ? documentKeys.detail(taskId) : [...documentKeys.all, "detail", "empty"],
    queryFn: async () => {
      const task = await getDocumentTask(taskId!);
      await queryClient.invalidateQueries({
        queryKey: documentKeys.list(),
      });
      return task;
    },
    enabled: enabled && Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && shouldPollDocumentTask(status) ? 2000 : false;
    },
    refetchIntervalInBackground: false,
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });
}
```

- [ ] **Step 3: Run the existing tests to verify the API layer compiles cleanly**

Run: `npm run test -- --run src/features/documents/documents.utils.test.ts src/features/chat/chat.utils.test.ts src/features/auth/auth.storage.test.ts src/lib/api-error.test.ts`  
Expected: PASS

- [ ] **Step 4: Run build to verify query and API integration compiles**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents/documents.api.ts frontend/src/features/documents/documents.queries.ts
git commit -m "feat: add document api and query hooks"
```

### Task 3: Replace Static Documents Page With Real Upload And Detail Flow

**Files:**
- Modify: `frontend/src/pages/documents/documents-page.tsx`
- Modify: `frontend/src/app/styles.css`

- [ ] **Step 1: Replace static mock rendering with real query state**

```tsx
// frontend/src/pages/documents/documents-page.tsx
import { Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useAppStore } from "@/app/store";
import { EmptyState } from "@/components/shared/empty-state";
import {
  useDocumentTasksQuery,
  usePollingDocumentTaskQuery,
  useUploadDocumentTaskMutation,
} from "@/features/documents/documents.queries";
import {
  buildDocumentSummary,
  getDocumentProgressLabel,
  isDocumentTaskTerminal,
} from "@/features/documents/documents.utils";
import { getErrorMessage, parseApiError } from "@/lib/api-error";

const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
const [selectedFile, setSelectedFile] = useState<File | null>(null);
const [taskType, setTaskType] = useState<"summary" | "conclusions" | "compare">("summary");
const [language, setLanguage] = useState<"zh" | "en">("zh");
const [uploadError, setUploadError] = useState("");

const isAuthenticated = useAppStore((state) => state.isAuthenticated);
const currentTerm = useAppStore((state) => state.currentTerm);

const tasksQuery = useDocumentTasksQuery(isAuthenticated);
const uploadMutation = useUploadDocumentTaskMutation();
const detailQuery = usePollingDocumentTaskQuery(selectedTaskId, Boolean(selectedTaskId));
```

- [ ] **Step 2: Add automatic selection behavior**

```tsx
useEffect(() => {
  if (tasksQuery.data?.items.length && !selectedTaskId) {
    setSelectedTaskId(tasksQuery.data.items[0].id);
  }
}, [tasksQuery.data?.items, selectedTaskId]);

useEffect(() => {
  if (uploadMutation.data?.id) {
    setSelectedTaskId(uploadMutation.data.id);
  }
}, [uploadMutation.data?.id]);
```

- [ ] **Step 3: Add upload form submission**

```tsx
function handleUpload() {
  if (!selectedFile || uploadMutation.isPending) {
    return;
  }

  setUploadError("");
  uploadMutation.mutate(
    {
      file: selectedFile,
      termId: currentTerm.id,
      taskType,
      language,
    },
    {
      onSuccess: () => {
        setSelectedFile(null);
      },
      onError: (error) => {
        const parsed = parseApiError(error);
        if (parsed.status === 413) {
          setUploadError("PDF 超出服务端限制，请压缩后重试。");
          return;
        }
        setUploadError(getErrorMessage(error, "上传失败，请稍后重试。"));
      },
    },
  );
}
```

- [ ] **Step 4: Render explicit list, detail, and failed state blocks**

```tsx
const selectedTask = detailQuery.data ?? null;
const summary = selectedTask ? buildDocumentSummary(selectedTask) : { summary: "", bulletPoints: [] };
const showPendingResult = selectedTask && !isDocumentTaskTerminal(selectedTask.status);
```

Use these UI rules:

- 列表区：
  - loading 时显示 `EmptyState`
  - error 时显示重试按钮
  - items 渲染真实 `filename / current_stage / result_preview / status`
- 详情区：
  - 未选择任务时显示空状态
  - loading 时显示“正在同步任务详情”
  - `pending/running` 时展示“结果尚未生成”
  - `done` 时展示 `summary.summary` 和 `summary.bulletPoints`
  - `failed` 时展示 `error_code` 与 `error_message`

- [ ] **Step 5: Add minimal styles for upload form inputs**

```css
/* frontend/src/app/styles.css */
.upload-panel {
  display: grid;
  gap: 14px;
}

.upload-controls {
  display: grid;
  gap: 12px;
}

.upload-grid {
  display: grid;
  gap: 12px;
}

.upload-select {
  width: 100%;
  border: 1px solid var(--border-strong);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  padding: 14px 16px;
  color: var(--foreground);
  outline: none;
}

.upload-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
```

- [ ] **Step 6: Run build to verify the page compiles**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/documents/documents-page.tsx frontend/src/app/styles.css
git commit -m "feat: connect documents page to real document tasks"
```

### Task 4: Verify Full Documents Flow

**Files:**
- No additional files

- [ ] **Step 1: Run the frontend tests**

Run: `npm run test -- --run`  
Expected: PASS

- [ ] **Step 2: Run the production build**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 3: Verify manual document flow against backend**

Run:

```bash
npm run dev
```

Manual checklist:

- `/app/documents` loads after login
- 任务列表可正常加载
- 选择任务后详情可正常显示
- 上传一个 PDF 后返回 `202`
- 新任务会自动被选中
- 新任务在 `pending/running` 时继续轮询
- 进入 `done/failed` 后停止轮询
- `done` 时能看到 `summary` 和 `bullet_points`
- `failed` 时能看到 `error_code` 和 `error_message`

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat: finish frontend documents round4 integration"
```

## Self-Review

- Spec coverage:
  - 上传、列表、详情、状态驱动轮询、上传成功自动选中、失败原因展示都分别覆盖在 Task 2-4 中。
  - 非目标项如 SSE、多文件批处理、Dashboard 真实统计未纳入任务，范围保持一致。
- Placeholder scan:
  - 已移除 `TODO/TBD`；每个任务都给出文件、命令和预期结果。
- Type consistency:
  - `task_type / language / term_id / current_stage / result.summary / result.bullet_points / error_code / error_message / pending/running/done/failed` 与 `spec/contract.yaml` 保持一致。

Plan complete and saved to `docs/superpowers/plans/2026-05-06-frontend-round4-documents.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
