# Frontend Round 5 Topics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `frontend/` 中完成 `/app/topics` 的真实列表与详情联调，支持当前学期题目浏览、默认选中首条题目，以及在双栏布局中切换查看详情。

**Architecture:** 延续现有前端分层：Zustand 继续只承担登录态与当前学期，Axios 继续负责鉴权和错误透传，Topics 的服务器状态全部由 TanStack Query 管理。页面只维护 `selectedTopicId` 这一处局部状态；列表与详情分别对应独立 query，不引入轮询，也不扩展到志愿或推荐链路。

**Tech Stack:** React 19, Vite 7, TypeScript, React Router, Tailwind CSS v4, shadcn/ui, TanStack Query, Zustand, Axios, Vitest

---

## File Structure

- Modify: `frontend/src/pages/topics/topics-page.tsx`
- Create: `frontend/src/features/topics/topics.types.ts`
- Create: `frontend/src/features/topics/topics.utils.ts`
- Create: `frontend/src/features/topics/topics.api.ts`
- Create: `frontend/src/features/topics/topics.queries.ts`
- Create: `frontend/src/features/topics/topics.utils.test.ts`

### Task 1: Add Topic Types, Mapping Helpers, And Utility Tests

**Files:**
- Create: `frontend/src/features/topics/topics.types.ts`
- Create: `frontend/src/features/topics/topics.utils.ts`
- Create: `frontend/src/features/topics/topics.utils.test.ts`

- [ ] **Step 1: Write the failing utility test**

```ts
// frontend/src/features/topics/topics.utils.test.ts
import { describe, expect, it } from "vitest";

import {
  buildTopicCapacityLabel,
  getTopicKeywordGroups,
  getTopicStatusLabel,
} from "@/features/topics/topics.utils";
import {
  mapTopicDto,
  type TopicDto,
} from "@/features/topics/topics.types";

const topicDto: TopicDto = {
  id: "topic-1",
  title: "面向毕业设计场景的 AI 学术助手工作台设计与实现",
  summary: "围绕异步聊天、PDF 文档处理与任务协同构建学生端产品。",
  requirements: "熟悉 React、Flask、异步任务队列与学术场景分析。",
  tech_keywords: ["AI 助手", "异步任务"],
  capacity: 2,
  selected_count: 1,
  teacher_id: "teacher-1",
  term_id: "term-2026-spring",
  status: "published",
  portrait: {
    keywords: ["工作台", "文档理解"],
    extracted_at: "2026-05-06T00:00:00Z",
  },
  llm_keyword_job_id: "job-1",
  llm_keyword_job_status: "done",
  created_at: "2026-05-06T00:00:00Z",
  updated_at: "2026-05-06T00:00:00Z",
};

describe("topics.utils", () => {
  it("maps topic dto into frontend model", () => {
    const topic = mapTopicDto(topicDto);

    expect(topic.techKeywords).toEqual(["AI 助手", "异步任务"]);
    expect(topic.selectedCount).toBe(1);
    expect(topic.portrait?.keywords).toEqual(["工作台", "文档理解"]);
    expect(topic.llmKeywordJobStatus).toBe("done");
  });

  it("formats topic status labels", () => {
    expect(getTopicStatusLabel("published")).toBe("可选题");
    expect(getTopicStatusLabel("pending_review")).toBe("待审核");
  });

  it("formats capacity labels", () => {
    const topic = mapTopicDto(topicDto);
    expect(buildTopicCapacityLabel(topic)).toBe("1 / 2 人");
  });

  it("prefers portrait keywords when available", () => {
    const topic = mapTopicDto(topicDto);

    expect(getTopicKeywordGroups(topic)).toEqual({
      primary: ["AI 助手", "异步任务"],
      derived: ["工作台", "文档理解"],
    });
  });
});
```

- [ ] **Step 2: Run the utility test to verify it fails**

Run: `npm run test -- --run src/features/topics/topics.utils.test.ts`  
Expected: FAIL with import-not-found errors for `topics.types` and `topics.utils`.

- [ ] **Step 3: Add topic types, DTO mapping, and pure utilities**

```ts
// frontend/src/features/topics/topics.types.ts
import type { AsyncTaskStatus } from "@/features/chat/chat.types";

export type TopicStatus = "draft" | "pending_review" | "published" | "rejected" | "closed";

export type PaginatedResponseDto<T> = {
  page: number;
  page_size: number;
  total: number;
  items: T[];
};

export type PaginatedResponse<T> = {
  page: number;
  pageSize: number;
  total: number;
  items: T[];
};

export type TopicPortraitDto = {
  keywords?: string[];
  extracted_at?: string | null;
} | null;

export type TopicPortrait = {
  keywords: string[];
  extractedAt?: string | null;
} | null;

export type TopicDto = {
  id: string;
  title: string;
  summary: string;
  requirements: string;
  tech_keywords?: string[];
  capacity: number;
  selected_count: number;
  teacher_id: string;
  term_id: string;
  status: TopicStatus;
  portrait?: TopicPortraitDto;
  llm_keyword_job_id?: string | null;
  llm_keyword_job_status?: AsyncTaskStatus | null;
  created_at: string;
  updated_at: string;
};

export type Topic = {
  id: string;
  title: string;
  summary: string;
  requirements: string;
  techKeywords: string[];
  capacity: number;
  selectedCount: number;
  teacherId: string;
  termId: string;
  status: TopicStatus;
  portrait?: TopicPortrait;
  llmKeywordJobId?: string | null;
  llmKeywordJobStatus?: AsyncTaskStatus | null;
  createdAt: string;
  updatedAt: string;
};

export function mapPaginatedResponseDto<TDto, TModel>(
  response: PaginatedResponseDto<TDto>,
  mapItem: (item: TDto) => TModel,
): PaginatedResponse<TModel> {
  return {
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
    items: response.items.map(mapItem),
  };
}

export function mapTopicPortraitDto(
  portrait?: TopicPortraitDto,
): TopicPortrait | undefined {
  if (portrait === undefined) {
    return undefined;
  }

  if (portrait === null) {
    return null;
  }

  return {
    keywords: portrait.keywords ?? [],
    extractedAt: portrait.extracted_at,
  };
}

export function mapTopicDto(topic: TopicDto): Topic {
  return {
    id: topic.id,
    title: topic.title,
    summary: topic.summary,
    requirements: topic.requirements,
    techKeywords: topic.tech_keywords ?? [],
    capacity: topic.capacity,
    selectedCount: topic.selected_count,
    teacherId: topic.teacher_id,
    termId: topic.term_id,
    status: topic.status,
    portrait: mapTopicPortraitDto(topic.portrait),
    llmKeywordJobId: topic.llm_keyword_job_id,
    llmKeywordJobStatus: topic.llm_keyword_job_status,
    createdAt: topic.created_at,
    updatedAt: topic.updated_at,
  };
}
```

```ts
// frontend/src/features/topics/topics.utils.ts
import type { Topic, TopicStatus } from "@/features/topics/topics.types";

const topicStatusLabels: Record<TopicStatus, string> = {
  draft: "草稿",
  pending_review: "待审核",
  published: "可选题",
  rejected: "已驳回",
  closed: "已关闭",
};

export function getTopicStatusLabel(status: TopicStatus) {
  return topicStatusLabels[status];
}

export function buildTopicCapacityLabel(topic: Pick<Topic, "selectedCount" | "capacity">) {
  return `${topic.selectedCount} / ${topic.capacity} 人`;
}

export function getTopicKeywordGroups(topic: Pick<Topic, "techKeywords" | "portrait">) {
  return {
    primary: topic.techKeywords,
    derived: topic.portrait?.keywords ?? [],
  };
}
```

- [ ] **Step 4: Run the utility test to verify it passes**

Run: `npm run test -- --run src/features/topics/topics.utils.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/topics/topics.types.ts frontend/src/features/topics/topics.utils.ts frontend/src/features/topics/topics.utils.test.ts
git commit -m "test: add topic utility coverage"
```

### Task 2: Build Topic API Layer And Query Hooks

**Files:**
- Create: `frontend/src/features/topics/topics.api.ts`
- Create: `frontend/src/features/topics/topics.queries.ts`

- [ ] **Step 1: Add the topic HTTP methods**

```ts
// frontend/src/features/topics/topics.api.ts
import { apiClient } from "@/lib/axios";
import type {
  PaginatedResponseDto,
  Topic,
  TopicDto,
} from "@/features/topics/topics.types";
import {
  mapPaginatedResponseDto,
  mapTopicDto,
} from "@/features/topics/topics.types";

export async function getTopics(termId: string) {
  const response = await apiClient.get<PaginatedResponseDto<TopicDto>>("/topics", {
    params: {
      term_id: termId,
      page: 1,
      page_size: 50,
    },
  });

  return mapPaginatedResponseDto(response.data, mapTopicDto);
}

export async function getTopic(topicId: string) {
  const response = await apiClient.get<TopicDto>(`/topics/${topicId}`);
  return mapTopicDto(response.data);
}
```

- [ ] **Step 2: Add TanStack Query hooks for list and detail**

```ts
// frontend/src/features/topics/topics.queries.ts
import { useQuery } from "@tanstack/react-query";

import { getTopic, getTopics } from "@/features/topics/topics.api";
import type { Topic } from "@/features/topics/topics.types";

export const topicKeys = {
  all: ["topics"] as const,
  list: (termId: string) => [...topicKeys.all, "list", termId] as const,
  detail: (topicId: string) => [...topicKeys.all, "detail", topicId] as const,
};

export function useTopicsQuery(enabled: boolean, termId: string) {
  return useQuery({
    queryKey: topicKeys.list(termId),
    queryFn: () => getTopics(termId),
    enabled,
  });
}

export function useTopicQuery(topicId: string | null, enabled: boolean) {
  return useQuery<Topic>({
    queryKey: topicId ? topicKeys.detail(topicId) : [...topicKeys.all, "detail", "empty"],
    queryFn: async () => getTopic(topicId!),
    enabled: enabled && Boolean(topicId),
  });
}
```

- [ ] **Step 3: Run the focused tests to verify the new topic layer compiles**

Run: `npm run test -- --run src/features/topics/topics.utils.test.ts src/features/chat/chat.utils.test.ts src/features/auth/auth.storage.test.ts src/lib/api-error.test.ts`  
Expected: PASS

- [ ] **Step 4: Run build to verify query and API integration compiles**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/topics/topics.api.ts frontend/src/features/topics/topics.queries.ts
git commit -m "feat: add topic api and query hooks"
```

### Task 3: Replace Static Topics Page With Real List And Detail Flow

**Files:**
- Modify: `frontend/src/pages/topics/topics-page.tsx`

- [ ] **Step 1: Replace static mock rendering with real query state**

```tsx
// frontend/src/pages/topics/topics-page.tsx
import { useEffect, useMemo, useState } from "react";

import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import {
  useTopicQuery,
  useTopicsQuery,
} from "@/features/topics/topics.queries";
import {
  buildTopicCapacityLabel,
  getTopicKeywordGroups,
  getTopicStatusLabel,
} from "@/features/topics/topics.utils";
import { getErrorMessage } from "@/lib/api-error";

const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);

const isAuthenticated = useAppStore((state) => state.isAuthenticated);
const currentTerm = useAppStore((state) => state.currentTerm);

const topicsQuery = useTopicsQuery(isAuthenticated, currentTerm.id);
const detailQuery = useTopicQuery(selectedTopicId, Boolean(selectedTopicId));
```

- [ ] **Step 2: Add automatic selection behavior**

```tsx
const topics = useMemo(() => topicsQuery.data?.items ?? [], [topicsQuery.data?.items]);

useEffect(() => {
  if (!topics.length) {
    if (selectedTopicId !== null) {
      setSelectedTopicId(null);
    }
    return;
  }

  if (selectedTopicId && topics.some((topic) => topic.id === selectedTopicId)) {
    return;
  }

  setSelectedTopicId(topics[0].id);
}, [selectedTopicId, topics]);
```

- [ ] **Step 3: Render explicit list, detail, loading, and error states**

Use these UI rules:

- 列表区：
  - loading 时显示 `EmptyState`
  - error 时显示重试按钮
  - items 渲染真实 `title / summary / techKeywords / status / selectedCount / capacity`
- 详情区：
  - 未选择题目时显示空状态
  - loading 时显示“正在同步题目详情”
  - error 时显示重试按钮
  - success 时展示 `summary / requirements / techKeywords / portrait.keywords / teacherId / termId / updatedAt`

- [ ] **Step 4: Remove mock dependency and wire the detail labels**

```tsx
const selectedTopic = detailQuery.data?.id === selectedTopicId ? detailQuery.data : null;
const keywordGroups = selectedTopic
  ? getTopicKeywordGroups(selectedTopic)
  : { primary: [], derived: [] };
```

Render these content rules:

- 主状态徽标使用 `getTopicStatusLabel`
- 容量文案使用 `buildTopicCapacityLabel`
- `keywordGroups.primary` 展示为“技术关键词”
- `keywordGroups.derived` 非空时展示为“系统抽取关键词”
- `llmKeywordJobStatus` 非空时展示轻提示，不做轮询

- [ ] **Step 5: Run build to verify the page compiles**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/topics/topics-page.tsx
git commit -m "feat: connect topics page to real topic data"
```

### Task 4: Verify Full Topics Flow

**Files:**
- No additional files

- [ ] **Step 1: Run the frontend tests**

Run: `npm run test -- --run`  
Expected: PASS

- [ ] **Step 2: Run the production build**

Run: `npm run build`  
Expected: PASS

- [ ] **Step 3: Verify manual topics flow against backend**

Run:

```bash
npm run dev
```

Manual checklist:

- `/app/topics` loads after login
- 题目列表可正常加载
- 首条题目会自动选中
- 点击其他题目后详情可正常切换
- 列表区错误态可重试
- 详情区错误态可重试
- 详情区能看到状态、研究要求、关键词和容量信息

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat: finish frontend topics round5 integration"
```

## Self-Review

- Spec coverage:
  - 当前学期题目列表、单题详情、默认选中、双栏切换、错误态重试都分别覆盖在 Task 2-4 中。
  - 非目标项如志愿提交、推荐接口、教师侧操作、异步轮询未纳入任务，范围保持一致。
- Placeholder scan:
  - 已移除 `TODO/TBD`；每个任务都给出文件、命令和预期结果。
- Type consistency:
  - `tech_keywords / selected_count / teacher_id / term_id / status / portrait.keywords / llm_keyword_job_status` 与 `spec/contract.yaml` 保持一致，前端页面只消费 camelCase 模型。

Plan complete and saved to `docs/superpowers/plans/2026-05-06-frontend-round5-topics.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
