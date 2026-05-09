# Frontend Round 3 Login Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `frontend/` 中完成真实登录与 Chat 主链路接入，支持 `access_token` 持久化、会话与消息真实加载、发消息异步受理，以及基于 `job_id` 的状态驱动轮询。

**Architecture:** 认证与当前学期摘要继续放在 Zustand 中，服务器状态统一交给 TanStack Query。Axios 负责鉴权注入与统一错误透传，页面层只组合 query/mutation 状态和展示。聊天发送后先插入 `202` 返回的占位 assistant 消息，再通过查询 `GET /api/v1/chat/jobs/{job_id}` 驱动消息列表刷新，直到 `done` 或 `failed` 停止。

**Tech Stack:** React 19, Vite 7, TypeScript, React Router, Tailwind CSS v4, shadcn/ui, TanStack Query, Zustand, Axios, Vitest

---

## File Structure

- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/app/providers.tsx`
- Modify: `frontend/src/app/store.ts`
- Modify: `frontend/src/lib/axios.ts`
- Modify: `frontend/src/pages/login/login-page.tsx`
- Modify: `frontend/src/pages/chat/chat-page.tsx`
- Modify: `frontend/src/routes/protected-layout.tsx`
- Modify: `frontend/src/components/layout/app-header.tsx`
- Create: `frontend/src/lib/api-error.ts`
- Create: `frontend/src/features/auth/auth.types.ts`
- Create: `frontend/src/features/auth/auth.storage.ts`
- Create: `frontend/src/features/auth/auth.api.ts`
- Create: `frontend/src/features/chat/chat.types.ts`
- Create: `frontend/src/features/chat/chat.utils.ts`
- Create: `frontend/src/features/chat/chat.api.ts`
- Create: `frontend/src/features/chat/chat.queries.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/lib/api-error.test.ts`
- Create: `frontend/src/features/auth/auth.storage.test.ts`
- Create: `frontend/src/features/chat/chat.utils.test.ts`

### Task 1: Add Test Harness And Red Tests

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/lib/api-error.test.ts`
- Create: `frontend/src/features/auth/auth.storage.test.ts`
- Create: `frontend/src/features/chat/chat.utils.test.ts`

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/src/lib/api-error.test.ts
import { describe, expect, it } from "vitest";
import { AxiosError } from "axios";

import { getErrorMessage, parseApiError } from "@/lib/api-error";

describe("parseApiError", () => {
  it("reads ErrorEnvelope fields", () => {
    const error = new AxiosError("Request failed", "400", undefined, undefined, {
      data: {
        error: {
          code: "VALIDATION_ERROR",
          message: "username and password are required",
          details: { field: "username" },
        },
      },
      status: 400,
      statusText: "Bad Request",
      headers: {},
      config: {} as never,
    });

    expect(parseApiError(error)).toEqual({
      code: "VALIDATION_ERROR",
      message: "username and password are required",
      details: { field: "username" },
      status: 400,
    });
  });

  it("falls back to generic message", () => {
    expect(getErrorMessage(new Error("boom"), "默认文案")).toBe("默认文案");
  });
});
```

```ts
// frontend/src/features/auth/auth.storage.test.ts
import { beforeEach, describe, expect, it } from "vitest";

import {
  clearAuthSession,
  loadAuthSession,
  saveAuthSession,
} from "@/features/auth/auth.storage";

const session = {
  accessToken: "token-123",
  expiresIn: 3600,
  user: {
    id: "user-1",
    username: "student-a",
    role: "student" as const,
    display_name: "Student A",
  },
};

describe("auth.storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("saves and loads auth session", () => {
    saveAuthSession(session);
    expect(loadAuthSession()).toEqual(session);
  });

  it("returns null for invalid payload", () => {
    localStorage.setItem("frontend.auth.session", "{bad json");
    expect(loadAuthSession()).toBeNull();
  });

  it("clears persisted session", () => {
    saveAuthSession(session);
    clearAuthSession();
    expect(loadAuthSession()).toBeNull();
  });
});
```

```ts
// frontend/src/features/chat/chat.utils.test.ts
import { describe, expect, it } from "vitest";

import { isAsyncTaskTerminal, shouldPollChatJob } from "@/features/chat/chat.utils";

describe("chat.utils", () => {
  it("treats done and failed as terminal", () => {
    expect(isAsyncTaskTerminal("done")).toBe(true);
    expect(isAsyncTaskTerminal("failed")).toBe(true);
  });

  it("keeps polling for pending and running only", () => {
    expect(shouldPollChatJob("pending")).toBe(true);
    expect(shouldPollChatJob("running")).toBe(true);
    expect(shouldPollChatJob("done")).toBe(false);
    expect(shouldPollChatJob("failed")).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm run test -- --run src/lib/api-error.test.ts src/features/auth/auth.storage.test.ts src/features/chat/chat.utils.test.ts`  
Expected: FAIL with module-not-found errors for `api-error`, `auth.storage`, and `chat.utils`, plus missing `test` script.

- [ ] **Step 3: Add minimal test tooling**

```json
// frontend/package.json
{
  "scripts": {
    "test": "vitest"
  },
  "devDependencies": {
    "vitest": "^3.2.4",
    "jsdom": "^26.1.0"
  }
}
```

```ts
// frontend/vite.config.ts
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
```

```ts
// frontend/src/test/setup.ts
import { afterEach } from "vitest";

afterEach(() => {
  localStorage.clear();
});
```

- [ ] **Step 4: Run tests again to verify they still fail for missing implementation**

Run: `npm run test -- --run src/lib/api-error.test.ts src/features/auth/auth.storage.test.ts src/features/chat/chat.utils.test.ts`  
Expected: FAIL with imports not found, but Vitest starts successfully.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/vite.config.ts frontend/src/test/setup.ts frontend/src/lib/api-error.test.ts frontend/src/features/auth/auth.storage.test.ts frontend/src/features/chat/chat.utils.test.ts
git commit -m "test: add frontend round3 test harness"
```

### Task 2: Build Shared Error Parsing And Auth Persistence

**Files:**
- Modify: `frontend/src/app/store.ts`
- Modify: `frontend/src/lib/axios.ts`
- Create: `frontend/src/lib/api-error.ts`
- Create: `frontend/src/features/auth/auth.types.ts`
- Create: `frontend/src/features/auth/auth.storage.ts`
- Create: `frontend/src/features/auth/auth.api.ts`
- Test: `frontend/src/lib/api-error.test.ts`
- Test: `frontend/src/features/auth/auth.storage.test.ts`

- [ ] **Step 1: Implement the shared auth and error modules**

```ts
// frontend/src/features/auth/auth.types.ts
export type UserRole = "student" | "teacher" | "admin";

export type AuthUser = {
  id?: string;
  username: string;
  role: UserRole;
  display_name?: string | null;
};

export type LoginRequest = {
  username: string;
  password: string;
};

export type LoginResponse = {
  token_type: "Bearer";
  access_token: string;
  expires_in: number;
  user: AuthUser;
};

export type AuthSession = {
  accessToken: string;
  expiresIn: number;
  user: AuthUser;
};
```

```ts
// frontend/src/features/auth/auth.storage.ts
import type { AuthSession } from "@/features/auth/auth.types";

const AUTH_STORAGE_KEY = "frontend.auth.session";

export function loadAuthSession(): AuthSession | null {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<AuthSession>;
    if (
      typeof parsed.accessToken !== "string" ||
      typeof parsed.expiresIn !== "number" ||
      !parsed.user ||
      typeof parsed.user.username !== "string" ||
      typeof parsed.user.role !== "string"
    ) {
      return null;
    }

    return parsed as AuthSession;
  } catch {
    return null;
  }
}

export function saveAuthSession(session: AuthSession) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function clearAuthSession() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}
```

```ts
// frontend/src/lib/api-error.ts
import { isAxiosError } from "axios";

export type ApiErrorInfo = {
  code?: string;
  message: string;
  details?: Record<string, unknown>;
  status?: number;
};

export function parseApiError(error: unknown): ApiErrorInfo {
  if (isAxiosError(error)) {
    const envelope = error.response?.data as
      | { error?: { code?: string; message?: string; details?: Record<string, unknown> } }
      | undefined;

    return {
      code: envelope?.error?.code,
      message: envelope?.error?.message ?? error.message,
      details: envelope?.error?.details,
      status: error.response?.status,
    };
  }

  if (error instanceof Error) {
    return { message: error.message };
  }

  return { message: "unknown error" };
}

export function getErrorMessage(error: unknown, fallback: string) {
  const parsed = parseApiError(error);
  return parsed.message || fallback;
}
```

```ts
// frontend/src/features/auth/auth.api.ts
import { apiClient } from "@/lib/axios";
import type { LoginRequest, LoginResponse } from "@/features/auth/auth.types";

export async function login(payload: LoginRequest) {
  const response = await apiClient.post<LoginResponse>("/auth/login", payload);
  return response.data;
}
```

```ts
// frontend/src/app/store.ts
import { create } from "zustand";

import { clearAuthSession, loadAuthSession, saveAuthSession } from "@/features/auth/auth.storage";
import type { AuthSession, AuthUser } from "@/features/auth/auth.types";

type TermSummary = {
  id: string;
  name: string;
};

type AppState = {
  isAuthReady: boolean;
  isAuthenticated: boolean;
  accessToken: string | null;
  currentUser: AuthUser | null;
  currentTerm: TermSummary;
  hydrateAuth: () => void;
  login: (session: AuthSession) => void;
  logout: () => void;
};

export const useAppStore = create<AppState>((set) => ({
  isAuthReady: false,
  isAuthenticated: false,
  accessToken: null,
  currentUser: null,
  currentTerm: {
    id: "term-2026-spring",
    name: "2026 春季学期",
  },
  hydrateAuth: () => {
    const session = loadAuthSession();
    if (!session) {
      set({ isAuthReady: true, isAuthenticated: false, accessToken: null, currentUser: null });
      return;
    }

    set({
      isAuthReady: true,
      isAuthenticated: true,
      accessToken: session.accessToken,
      currentUser: session.user,
    });
  },
  login: (session) => {
    saveAuthSession(session);
    set({
      isAuthReady: true,
      isAuthenticated: true,
      accessToken: session.accessToken,
      currentUser: session.user,
    });
  },
  logout: () => {
    clearAuthSession();
    set({ isAuthReady: true, isAuthenticated: false, accessToken: null, currentUser: null });
  },
}));
```

```ts
// frontend/src/lib/axios.ts
import axios from "axios";

import { clearAuthSession, loadAuthSession } from "@/features/auth/auth.storage";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  const session = loadAuthSession();
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuthSession();
    }
    return Promise.reject(error);
  },
);
```

- [ ] **Step 2: Run unit tests to verify they pass**

Run: `npm run test -- --run src/lib/api-error.test.ts src/features/auth/auth.storage.test.ts`  
Expected: PASS

- [ ] **Step 3: Refactor imports and store access points**

```ts
// frontend/src/features/auth/auth-store.ts
export { useAppStore as useAuthStore } from "@/app/store";
```

- [ ] **Step 4: Run the same unit tests again**

Run: `npm run test -- --run src/lib/api-error.test.ts src/features/auth/auth.storage.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/store.ts frontend/src/lib/axios.ts frontend/src/lib/api-error.ts frontend/src/features/auth/auth.types.ts frontend/src/features/auth/auth.storage.ts frontend/src/features/auth/auth.api.ts frontend/src/features/auth/auth-store.ts frontend/src/lib/api-error.test.ts frontend/src/features/auth/auth.storage.test.ts
git commit -m "feat: add frontend auth persistence and api error parsing"
```

### Task 3: Wire Auth Bootstrapping And Real Login Page

**Files:**
- Modify: `frontend/src/app/providers.tsx`
- Modify: `frontend/src/routes/protected-layout.tsx`
- Modify: `frontend/src/components/layout/app-header.tsx`
- Modify: `frontend/src/pages/login/login-page.tsx`

- [ ] **Step 1: Add auth hydration during app bootstrap**

```ts
// frontend/src/app/providers.tsx
import { useEffect, useState } from "react";

import { useAppStore } from "@/app/store";

export function AppProviders({ children }: PropsWithChildren) {
  const hydrateAuth = useAppStore((state) => state.hydrateAuth);

  useEffect(() => {
    hydrateAuth();
  }, [hydrateAuth]);

  // keep existing QueryClientProvider setup
}
```

- [ ] **Step 2: Guard protected routes on auth-ready state**

```ts
// frontend/src/routes/protected-layout.tsx
const { isAuthReady, isAuthenticated } = useAppStore((state) => ({
  isAuthReady: state.isAuthReady,
  isAuthenticated: state.isAuthenticated,
}));

if (!isAuthReady) {
  return null;
}

if (!isAuthenticated) {
  return <Navigate to="/login" replace />;
}
```

- [ ] **Step 3: Update the header to tolerate null user**

```ts
// frontend/src/components/layout/app-header.tsx
<Avatar>
  <AvatarFallback>{currentUser?.display_name?.slice(-2) ?? currentUser?.username?.slice(-2) ?? "访客"}</AvatarFallback>
</Avatar>
```

- [ ] **Step 4: Replace fake login with real mutation**

```tsx
// frontend/src/pages/login/login-page.tsx
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { login as loginRequest } from "@/features/auth/auth.api";
import { getErrorMessage } from "@/lib/api-error";

const [username, setUsername] = useState("api-login-user");
const [password, setPassword] = useState("correct-pass");
const [errorMessage, setErrorMessage] = useState("");

const mutation = useMutation({
  mutationFn: loginRequest,
  onSuccess: (data) => {
    login({
      accessToken: data.access_token,
      expiresIn: data.expires_in,
      user: data.user,
    });
    navigate("/app/dashboard", { replace: true });
  },
  onError: (error) => {
    setErrorMessage(getErrorMessage(error, "登录失败，请稍后重试。"));
  },
});

<Input id="student-id" value={username} onChange={(event) => setUsername(event.target.value)} />
<Input id="password" value={password} onChange={(event) => setPassword(event.target.value)} type="password" />
{errorMessage ? <p className="small" style={{ color: "var(--danger-foreground)" }}>{errorMessage}</p> : null}
<Button
  className="w-full"
  disabled={mutation.isPending}
  onClick={() => {
    setErrorMessage("");
    mutation.mutate({ username, password });
  }}
>
  {mutation.isPending ? "登录中…" : "进入 AI 学术助手工作台"}
</Button>
```

- [ ] **Step 5: Run build to verify auth wiring compiles**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/providers.tsx frontend/src/routes/protected-layout.tsx frontend/src/components/layout/app-header.tsx frontend/src/pages/login/login-page.tsx
git commit -m "feat: connect frontend login to auth api"
```

### Task 4: Add Chat Types, Queries, And Polling Helpers

**Files:**
- Create: `frontend/src/features/chat/chat.types.ts`
- Create: `frontend/src/features/chat/chat.utils.ts`
- Create: `frontend/src/features/chat/chat.api.ts`
- Create: `frontend/src/features/chat/chat.queries.ts`
- Test: `frontend/src/features/chat/chat.utils.test.ts`

- [ ] **Step 1: Implement chat types and polling helpers**

```ts
// frontend/src/features/chat/chat.types.ts
export type AsyncTaskStatus = "pending" | "running" | "done" | "failed";

export type PaginatedResponse<T> = {
  page: number;
  page_size: number;
  total: number;
  items: T[];
};

export type Conversation = {
  id: string;
  term_id: string;
  title?: string | null;
  context_type?: "general" | "topic" | "document";
  context_ref_id?: string | null;
  created_at: string;
  updated_at?: string;
};

export type Message = {
  id: string;
  conversation_id: string;
  role: "system" | "user" | "assistant";
  content: string;
  status?: AsyncTaskStatus | null;
  created_at: string;
  updated_at?: string;
};

export type ChatJob = {
  job_id: string;
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  status: AsyncTaskStatus;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};
```

```ts
// frontend/src/features/chat/chat.utils.ts
import type { AsyncTaskStatus } from "@/features/chat/chat.types";

export function isAsyncTaskTerminal(status: AsyncTaskStatus) {
  return status === "done" || status === "failed";
}

export function shouldPollChatJob(status: AsyncTaskStatus) {
  return status === "pending" || status === "running";
}
```

- [ ] **Step 2: Run chat utility tests to verify they pass**

Run: `npm run test -- --run src/features/chat/chat.utils.test.ts`  
Expected: PASS

- [ ] **Step 3: Implement HTTP methods and TanStack Query hooks**

```ts
// frontend/src/features/chat/chat.api.ts
import { apiClient } from "@/lib/axios";
import type {
  ChatJob,
  Conversation,
  Message,
  PaginatedResponse,
} from "@/features/chat/chat.types";

export async function getConversations() {
  const response = await apiClient.get<PaginatedResponse<Conversation>>("/conversations");
  return response.data;
}

export async function createConversation(payload: { term_id: string; title?: string; context_type?: "general" }) {
  const response = await apiClient.post<Conversation>("/conversations", payload);
  return response.data;
}

export async function getMessages(conversationId: string) {
  const response = await apiClient.get<PaginatedResponse<Message>>(`/conversations/${conversationId}/messages`, {
    params: { page: 1, page_size: 100, order: "asc" },
  });
  return response.data;
}

export async function postMessage(
  conversationId: string,
  payload: { content: string; client_request_id?: string; seq?: number },
) {
  const response = await apiClient.post<{
    job_id: string;
    user_message: Message;
    assistant_message: Message;
  }>(`/conversations/${conversationId}/messages`, payload);
  return response.data;
}

export async function getChatJob(jobId: string) {
  const response = await apiClient.get<ChatJob>(`/chat/jobs/${jobId}`);
  return response.data;
}
```

```ts
// frontend/src/features/chat/chat.queries.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createConversation, getChatJob, getConversations, getMessages, postMessage } from "@/features/chat/chat.api";
import { shouldPollChatJob } from "@/features/chat/chat.utils";

export const chatKeys = {
  all: ["chat"] as const,
  conversations: () => [...chatKeys.all, "conversations"] as const,
  messages: (conversationId: string) => [...chatKeys.all, "messages", conversationId] as const,
  job: (jobId: string) => [...chatKeys.all, "job", jobId] as const,
};

export function useConversationsQuery(enabled: boolean) {
  return useQuery({
    queryKey: chatKeys.conversations(),
    queryFn: getConversations,
    enabled,
  });
}

export function useMessagesQuery(conversationId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: conversationId ? chatKeys.messages(conversationId) : [...chatKeys.all, "messages", "empty"],
    queryFn: () => getMessages(conversationId!),
    enabled: enabled && Boolean(conversationId),
  });
}

export function useCreateConversationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createConversation,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
    },
  });
}

export function usePostMessageMutation(conversationId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { content: string; client_request_id?: string; seq?: number }) =>
      postMessage(conversationId!, payload),
    onSuccess: async () => {
      if (conversationId) {
        await queryClient.invalidateQueries({ queryKey: chatKeys.messages(conversationId) });
      }
    },
  });
}

export function useChatJobQuery(jobId: string | null, conversationId: string | null) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: jobId ? chatKeys.job(jobId) : [...chatKeys.all, "job", "empty"],
    queryFn: () => getChatJob(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && shouldPollChatJob(status) ? 2000 : false;
    },
    refetchIntervalInBackground: false,
    onSuccess: async (job) => {
      if (conversationId) {
        await queryClient.invalidateQueries({ queryKey: chatKeys.messages(conversationId) });
      }
    },
  });
}
```

- [ ] **Step 4: Run chat tests again**

Run: `npm run test -- --run src/features/chat/chat.utils.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/chat/chat.types.ts frontend/src/features/chat/chat.utils.ts frontend/src/features/chat/chat.api.ts frontend/src/features/chat/chat.queries.ts frontend/src/features/chat/chat.utils.test.ts
git commit -m "feat: add frontend chat api and polling hooks"
```

### Task 5: Replace Static Chat Page With Real Conversation Flow

**Files:**
- Modify: `frontend/src/pages/chat/chat-page.tsx`

- [ ] **Step 1: Build the real page flow**

```tsx
// frontend/src/pages/chat/chat-page.tsx
import { useEffect, useMemo, useState } from "react";
import { SendHorizonal } from "lucide-react";

import { useAppStore } from "@/app/store";
import {
  useChatJobQuery,
  useConversationsQuery,
  useCreateConversationMutation,
  useMessagesQuery,
  usePostMessageMutation,
} from "@/features/chat/chat.queries";
import { getErrorMessage } from "@/lib/api-error";

const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
const [draft, setDraft] = useState("");
const [activeJobId, setActiveJobId] = useState<string | null>(null);
const [sendError, setSendError] = useState("");

const isAuthenticated = useAppStore((state) => state.isAuthenticated);
const currentTerm = useAppStore((state) => state.currentTerm);

const conversationsQuery = useConversationsQuery(isAuthenticated);
const createConversationMutation = useCreateConversationMutation();

useEffect(() => {
  if (conversationsQuery.data?.items.length && !selectedConversationId) {
    setSelectedConversationId(conversationsQuery.data.items[0].id);
  }
}, [conversationsQuery.data?.items, selectedConversationId]);

useEffect(() => {
  if (
    conversationsQuery.isSuccess &&
    conversationsQuery.data.items.length === 0 &&
    !createConversationMutation.isPending &&
    !createConversationMutation.isSuccess
  ) {
    createConversationMutation.mutate({
      term_id: currentTerm.id,
      title: "通用学术咨询",
      context_type: "general",
    });
  }
}, [conversationsQuery, createConversationMutation, currentTerm.id]);

useEffect(() => {
  if (createConversationMutation.data?.id) {
    setSelectedConversationId(createConversationMutation.data.id);
  }
}, [createConversationMutation.data?.id]);

const messagesQuery = useMessagesQuery(selectedConversationId, Boolean(selectedConversationId));
const postMessageMutation = usePostMessageMutation(selectedConversationId);
const chatJobQuery = useChatJobQuery(activeJobId, selectedConversationId);

useEffect(() => {
  if (chatJobQuery.data?.status === "done" || chatJobQuery.data?.status === "failed") {
    setActiveJobId(null);
  }
}, [chatJobQuery.data?.status]);

const messages = useMemo(() => {
  const serverMessages = messagesQuery.data?.items ?? [];
  if (!postMessageMutation.data) return serverMessages;

  const ids = new Set(serverMessages.map((item) => item.id));
  return [
    ...serverMessages,
    ...[postMessageMutation.data.user_message, postMessageMutation.data.assistant_message].filter(
      (item) => !ids.has(item.id),
    ),
  ];
}, [messagesQuery.data?.items, postMessageMutation.data]);

// render loading, errors, conversation list, messages, and send action
```

- [ ] **Step 2: Render explicit async states and retry space**

```tsx
{chatJobQuery.data ? (
  <div className="detail-card">
    <p style={{ fontWeight: 600 }}>最近任务状态</p>
    <p className="muted small" style={{ marginTop: 10 }}>
      job_id: {chatJobQuery.data.job_id}
    </p>
    <div style={{ marginTop: 12 }}>
      <StatusBadge status={chatJobQuery.data.status} />
    </div>
    {chatJobQuery.data.error_message ? (
      <p className="small" style={{ marginTop: 10, color: "var(--danger-foreground)" }}>
        {chatJobQuery.data.error_message}
      </p>
    ) : null}
  </div>
) : (
  <div className="detail-card">
    <p style={{ fontWeight: 600 }}>最近任务状态</p>
    <p className="muted small" style={{ marginTop: 10 }}>
      当前没有正在轮询的 chat job。
    </p>
  </div>
)}
```

- [ ] **Step 3: Run focused build**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/chat/chat-page.tsx
git commit -m "feat: connect frontend chat page to real api"
```

### Task 6: Full Verification And Demo Walkthrough

**Files:**
- No additional code files

- [ ] **Step 1: Run the full frontend unit tests**

Run: `npm run test -- --run`  
Expected: PASS with the three utility test files green.

- [ ] **Step 2: Run the production build**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 3: Run the dev server**

Run: `npm run dev`  
Expected: Vite prints a local URL and serves the app without startup errors.

- [ ] **Step 4: Verify the main user path manually**

Run:

```bash
npm run dev
```

Manual checklist:

- `/login` loads and can submit real `username` / `password`
- 登录成功后跳转到 `/app/dashboard`
- 刷新页面后仍保留登录态
- 进入 `/app/chat` 后能加载会话列表
- 若无会话，自动创建 `general` 会话
- 发送消息后能看到用户消息和 assistant 占位消息
- `pending` / `running` 时继续轮询
- `done` / `failed` 时停止轮询

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat: finish frontend round3 login and chat integration"
```

## Self-Review

- Spec coverage:
  - 真实登录、`localStorage` 持久化、页面刷新恢复、会话列表、自动创建会话、消息列表、发送消息、`job_id` 轮询、终态停止、统一错误解析都已在 Task 2-5 覆盖。
  - 非目标项如 Documents、Dashboard 真实统计、SSE、refresh token 流程未纳入任务，范围保持一致。
- Placeholder scan:
  - 已移除 `TODO/TBD`；每个任务都有明确文件和验证命令。
- Type consistency:
  - `access_token / expires_in / token_type / term_id / job_id / status` 与 `spec/contract.yaml` 保持一致；轮询状态固定为 `pending / running / done / failed`。

Plan complete and saved to `docs/superpowers/plans/2026-05-06-frontend-round3-login-chat.md`. Since you asked me to continue in this session, I will execute it inline next.
