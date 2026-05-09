# Topics Real Analysis & Recommendation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the demo-only Topics analysis and recommendation logic in `frontend/` with contract-driven teacher analysis, student profile persistence, and backend recommendation results.

**Architecture:** Keep `/app/topics` as one workbench page with browse, teacher, and student modes. Expand the Topics data model to match the updated `contract.yaml`, add a small `users/me` feature layer, and use TanStack Query for topic detail polling and recommendation fetching after the student profile is saved. Delete the local mock workbench logic once the page is fully wired to real APIs.

**Tech Stack:** React, TypeScript, Vite, TanStack Query, Axios, Zustand, Vitest, shadcn/ui

---

## File Structure

### Existing files to modify

- `frontend/src/features/topics/topics.types.ts`
  - Expand `Topic.portrait` mapping and add recommendation DTO/model mapping.
- `frontend/src/features/topics/topics.api.ts`
  - Add create/update topic and recommendation API wrappers.
- `frontend/src/features/topics/topics.queries.ts`
  - Add polling helper, topic save mutations, and recommendation query hook.
- `frontend/src/features/topics/topics.utils.test.ts`
  - Extend topic mapping coverage for the expanded portrait shape.
- `frontend/src/pages/topics/topics-page.tsx`
  - Replace local demo analysis/recommendation behavior with real backend flows.

### New files to create

- `frontend/src/features/users/users.types.ts`
  - `UserMe`, `StudentProfile`, and `PatchUserMeRequest` DTO/model mapping.
- `frontend/src/features/users/users.types.test.ts`
  - Unit tests for `users/me` mapping.
- `frontend/src/features/users/users.api.ts`
  - `getUserMe` and `patchUserMe`.
- `frontend/src/features/users/users.queries.ts`
  - Query and mutation hooks for `users/me`.
- `frontend/src/features/topics/topics.queries.test.ts`
  - Unit tests for status-driven polling helper.
- `frontend/src/pages/topics/topics-page.utils.ts`
  - Pure helpers for topic draft payloads and student profile form hydration.
- `frontend/src/pages/topics/topics-page.utils.test.ts`
  - Unit tests for topic draft parsing and profile payload building.
- `frontend/src/pages/topics/topics-page.test.tsx`
  - Page-level smoke tests for teacher and student real-data rendering.

### Files to remove after integration

- `frontend/src/features/topics/topics-workbench.ts`
- `frontend/src/features/topics/topics-workbench.test.ts`

---

### Task 1: Expand Contract Mappings For Topics And Users

**Files:**
- Modify: `frontend/src/features/topics/topics.types.ts`
- Modify: `frontend/src/features/topics/topics.utils.test.ts`
- Create: `frontend/src/features/users/users.types.ts`
- Create: `frontend/src/features/users/users.types.test.ts`
- Test: `frontend/src/features/topics/topics.utils.test.ts`
- Test: `frontend/src/features/users/users.types.test.ts`

- [ ] **Step 1: Write the failing mapping tests**

```ts
// frontend/src/features/topics/topics.utils.test.ts
import { describe, expect, it } from "vitest";

import {
  mapRecommendationTopicListDto,
  mapTopicDto,
  type RecommendationTopicListDto,
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
    difficulty_label: "advanced",
    difficulty_reason: "需要同时覆盖前端、后端和异步任务。",
    required_capabilities: ["React", "Flask", "任务编排"],
    suitable_students: ["有完整项目经验的学生"],
    risks: ["范围较大，需要严格拆分阶段"],
    summary: "这是一个跨前后端与 AI 工作流整合的题目。",
    extracted_at: "2026-05-09T00:00:00Z",
  },
  llm_keyword_job_id: "job-1",
  llm_keyword_job_status: "done",
  created_at: "2026-05-06T00:00:00Z",
  updated_at: "2026-05-09T00:00:00Z",
};

const recommendationDto: RecommendationTopicListDto = {
  top_n: 10,
  items: [
    {
      topic_id: "topic-1",
      title: "面向毕业设计场景的 AI 学术助手工作台设计与实现",
      score: 92,
      explain: {
        matched_skills: ["React"],
        matched_keywords: ["异步任务"],
        matched_capabilities: ["前端实现", "任务编排"],
        difficulty_fit: "学生每周投入时间可覆盖进阶难度要求",
        capacity_status: "available",
        warnings: ["仍需补足推荐解释模块"],
        reasons: ["题目画像与学生画像高度重合"],
      },
    },
  ],
};

describe("topics.utils", () => {
  it("maps topic dto into frontend model with full portrait fields", () => {
    const topic = mapTopicDto(topicDto);

    expect(topic.portrait).toEqual({
      keywords: ["工作台", "文档理解"],
      difficultyLabel: "advanced",
      difficultyReason: "需要同时覆盖前端、后端和异步任务。",
      requiredCapabilities: ["React", "Flask", "任务编排"],
      suitableStudents: ["有完整项目经验的学生"],
      risks: ["范围较大，需要严格拆分阶段"],
      summary: "这是一个跨前后端与 AI 工作流整合的题目。",
      extractedAt: "2026-05-09T00:00:00Z",
    });
  });

  it("maps recommendation dto explain fields", () => {
    const result = mapRecommendationTopicListDto(recommendationDto);

    expect(result.topN).toBe(10);
    expect(result.items[0]?.explain?.matchedCapabilities).toEqual([
      "前端实现",
      "任务编排",
    ]);
    expect(result.items[0]?.explain?.capacityStatus).toBe("available");
  });
});
```

```ts
// frontend/src/features/users/users.types.test.ts
import { describe, expect, it } from "vitest";

import { mapUserMeDto, type UserMeDto } from "@/features/users/users.types";

describe("users.types", () => {
  it("maps user me dto and student profile into frontend model", () => {
    const dto: UserMeDto = {
      id: "user-1",
      username: "student-demo",
      role: "student",
      display_name: "联调学生",
      email: "student@example.com",
      student_profile: {
        interests: ["AI 学术助手", "选题推荐"],
        skills: ["React", "Flask"],
        keywords: ["画像", "异步任务"],
        goal: "希望完成可用于答辩演示的毕业设计",
        weekly_hours: 10,
      },
      teacher_profile: null,
    };

    expect(mapUserMeDto(dto)).toEqual({
      id: "user-1",
      username: "student-demo",
      role: "student",
      displayName: "联调学生",
      email: "student@example.com",
      studentProfile: {
        interests: ["AI 学术助手", "选题推荐"],
        skills: ["React", "Flask"],
        keywords: ["画像", "异步任务"],
        goal: "希望完成可用于答辩演示的毕业设计",
        weeklyHours: 10,
      },
      teacherProfile: null,
    });
  });
});
```

- [ ] **Step 2: Run the mapping tests and verify they fail**

Run:

```bash
cd frontend
npx vitest run src/features/topics/topics.utils.test.ts src/features/users/users.types.test.ts
```

Expected:

- `topics.utils.test.ts` fails because `mapTopicDto` and recommendation mapping do not yet expose the new portrait and explain fields.
- `users.types.test.ts` fails because `users.types.ts` does not exist yet.

- [ ] **Step 3: Implement the minimal DTO/model mapping**

```ts
// frontend/src/features/topics/topics.types.ts
import type { AsyncStatus } from "@/types/app";

export type TopicDifficultyLabel = "basic" | "intermediate" | "advanced";
export type RecommendationCapacityStatus = "available" | "nearly_full" | "full";

export type TopicPortraitDto = {
  keywords?: string[];
  difficulty_label?: TopicDifficultyLabel | null;
  difficulty_reason?: string | null;
  required_capabilities?: string[];
  suitable_students?: string[];
  risks?: string[];
  summary?: string | null;
  extracted_at?: string | null;
} | null;

export type TopicPortrait = {
  keywords: string[];
  difficultyLabel?: TopicDifficultyLabel | null;
  difficultyReason?: string | null;
  requiredCapabilities: string[];
  suitableStudents: string[];
  risks: string[];
  summary?: string | null;
  extractedAt?: string | null;
} | null;

export type RecommendationExplainDto = {
  matched_skills?: string[];
  matched_keywords?: string[];
  matched_capabilities?: string[];
  difficulty_fit?: string | null;
  capacity_status?: RecommendationCapacityStatus | null;
  warnings?: string[];
  reasons?: string[];
} | null;

export type RecommendationTopicItemDto = {
  topic_id: string;
  title: string;
  score: number;
  explain?: RecommendationExplainDto;
};

export type RecommendationTopicListDto = {
  items: RecommendationTopicItemDto[];
  top_n: number;
};

export type RecommendationExplain = {
  matchedSkills: string[];
  matchedKeywords: string[];
  matchedCapabilities: string[];
  difficultyFit?: string | null;
  capacityStatus?: RecommendationCapacityStatus | null;
  warnings: string[];
  reasons: string[];
} | null;

export type RecommendationTopicItem = {
  topicId: string;
  title: string;
  score: number;
  explain?: RecommendationExplain;
};

export type RecommendationTopicList = {
  items: RecommendationTopicItem[];
  topN: number;
};

export function mapTopicPortraitDto(portrait?: TopicPortraitDto): TopicPortrait | undefined {
  if (portrait === undefined) {
    return undefined;
  }

  if (portrait === null) {
    return null;
  }

  return {
    keywords: portrait.keywords ?? [],
    difficultyLabel: portrait.difficulty_label,
    difficultyReason: portrait.difficulty_reason,
    requiredCapabilities: portrait.required_capabilities ?? [],
    suitableStudents: portrait.suitable_students ?? [],
    risks: portrait.risks ?? [],
    summary: portrait.summary,
    extractedAt: portrait.extracted_at,
  };
}

export function mapRecommendationTopicListDto(
  response: RecommendationTopicListDto,
): RecommendationTopicList {
  return {
    topN: response.top_n,
    items: response.items.map((item) => ({
      topicId: item.topic_id,
      title: item.title,
      score: item.score,
      explain: item.explain
        ? {
            matchedSkills: item.explain.matched_skills ?? [],
            matchedKeywords: item.explain.matched_keywords ?? [],
            matchedCapabilities: item.explain.matched_capabilities ?? [],
            difficultyFit: item.explain.difficulty_fit,
            capacityStatus: item.explain.capacity_status,
            warnings: item.explain.warnings ?? [],
            reasons: item.explain.reasons ?? [],
          }
        : null,
    })),
  };
}
```

```ts
// frontend/src/features/users/users.types.ts
import type { UserRole } from "@/features/auth/auth.types";

export type StudentProfileDto = {
  interests?: string[];
  skills?: string[];
  keywords?: string[];
  goal?: string | null;
  weekly_hours?: number | null;
} | null;

export type UserMeDto = {
  id: string;
  username: string;
  role: UserRole;
  display_name: string;
  email?: string | null;
  student_profile?: StudentProfileDto;
  teacher_profile?: Record<string, unknown> | null;
};

export type StudentProfile = {
  interests: string[];
  skills: string[];
  keywords: string[];
  goal?: string | null;
  weeklyHours?: number | null;
} | null;

export type UserMe = {
  id: string;
  username: string;
  role: UserRole;
  displayName: string;
  email?: string | null;
  studentProfile?: StudentProfile;
  teacherProfile?: Record<string, unknown> | null;
};

export type PatchUserMeRequest = {
  display_name?: string;
  email?: string;
  student_profile?: {
    interests: string[];
    skills: string[];
    keywords: string[];
    goal?: string | null;
    weekly_hours?: number | null;
  } | null;
};

export function mapStudentProfileDto(profile?: StudentProfileDto): StudentProfile | undefined {
  if (profile === undefined) {
    return undefined;
  }

  if (profile === null) {
    return null;
  }

  return {
    interests: profile.interests ?? [],
    skills: profile.skills ?? [],
    keywords: profile.keywords ?? [],
    goal: profile.goal,
    weeklyHours: profile.weekly_hours,
  };
}

export function mapUserMeDto(dto: UserMeDto): UserMe {
  return {
    id: dto.id,
    username: dto.username,
    role: dto.role,
    displayName: dto.display_name,
    email: dto.email,
    studentProfile: mapStudentProfileDto(dto.student_profile),
    teacherProfile: dto.teacher_profile ?? null,
  };
}
```

- [ ] **Step 4: Run the mapping tests and verify they pass**

Run:

```bash
cd frontend
npx vitest run src/features/topics/topics.utils.test.ts src/features/users/users.types.test.ts
```

Expected:

- `topics.utils.test.ts` passes with the expanded portrait and recommendation mapping.
- `users.types.test.ts` passes with the new `users/me` mapping.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/topics/topics.types.ts frontend/src/features/topics/topics.utils.test.ts frontend/src/features/users/users.types.ts frontend/src/features/users/users.types.test.ts
git commit -m "feat(frontend): add topics and user contract mappings"
```

### Task 2: Add Pure Draft Helpers For Topics Page

**Files:**
- Create: `frontend/src/pages/topics/topics-page.utils.ts`
- Create: `frontend/src/pages/topics/topics-page.utils.test.ts`
- Test: `frontend/src/pages/topics/topics-page.utils.test.ts`

- [ ] **Step 1: Write the failing helper tests**

```ts
// frontend/src/pages/topics/topics-page.utils.test.ts
import { describe, expect, it } from "vitest";

import {
  buildCreateTopicRequest,
  buildPatchTopicRequest,
  buildStudentProfilePatch,
  mapStudentProfileToDraft,
  parseDraftTerms,
} from "@/pages/topics/topics-page.utils";

describe("topics-page.utils", () => {
  it("parses comma-like terms into unique values", () => {
    expect(parseDraftTerms("React，Flask, React\n异步任务")).toEqual([
      "React",
      "Flask",
      "异步任务",
    ]);
  });

  it("builds create topic payload from teacher draft", () => {
    expect(
      buildCreateTopicRequest(
        {
          title: "AI 学术助手工作台",
          summary: "面向毕业设计的工作台",
          requirements: "熟悉 React、Flask 和异步任务",
          keywords: "AI 助手，异步任务，工作台",
          capacity: "2",
        },
        "term-2026-spring",
      ),
    ).toEqual({
      title: "AI 学术助手工作台",
      summary: "面向毕业设计的工作台",
      requirements: "熟悉 React、Flask 和异步任务",
      tech_keywords: ["AI 助手", "异步任务", "工作台"],
      capacity: 2,
      term_id: "term-2026-spring",
    });
  });

  it("hydrates student draft from saved profile", () => {
    expect(
      mapStudentProfileToDraft({
        interests: ["AI 学术助手", "选题推荐"],
        skills: ["React", "Flask"],
        keywords: ["画像"],
        goal: "做一个适合答辩展示的系统",
        weeklyHours: 8,
      }),
    ).toEqual({
      interests: "AI 学术助手，选题推荐",
      skills: "React，Flask",
      keywords: "画像",
      goal: "做一个适合答辩展示的系统",
      weeklyHours: "8",
    });
  });

  it("builds patch user me payload from student draft", () => {
    expect(
      buildStudentProfilePatch({
        interests: "AI 学术助手，选题推荐",
        skills: "React，Flask",
        keywords: "画像，可解释推荐",
        goal: "做一个适合答辩展示的系统",
        weeklyHours: "10",
      }),
    ).toEqual({
      student_profile: {
        interests: ["AI 学术助手", "选题推荐"],
        skills: ["React", "Flask"],
        keywords: ["画像", "可解释推荐"],
        goal: "做一个适合答辩展示的系统",
        weekly_hours: 10,
      },
    });
  });
});
```

- [ ] **Step 2: Run the helper tests and verify they fail**

Run:

```bash
cd frontend
npx vitest run src/pages/topics/topics-page.utils.test.ts
```

Expected:

- Test run fails because `topics-page.utils.ts` does not exist yet.

- [ ] **Step 3: Implement the minimal helper file**

```ts
// frontend/src/pages/topics/topics-page.utils.ts
import type { PatchUserMeRequest, StudentProfile } from "@/features/users/users.types";

export type TeacherTopicDraft = {
  title: string;
  summary: string;
  requirements: string;
  keywords: string;
  capacity: string;
};

export type StudentProfileDraft = {
  interests: string;
  skills: string;
  keywords: string;
  goal: string;
  weeklyHours: string;
};

const splitPattern = /[\n,，、;；/|]+/;

export function parseDraftTerms(text: string) {
  const seen = new Map<string, string>();

  for (const chunk of text.split(splitPattern)) {
    const term = chunk.trim();
    const normalized = term.toLowerCase();

    if (!normalized || seen.has(normalized)) {
      continue;
    }

    seen.set(normalized, term);
  }

  return [...seen.values()];
}

export function buildCreateTopicRequest(draft: TeacherTopicDraft, termId: string) {
  return {
    title: draft.title.trim(),
    summary: draft.summary.trim(),
    requirements: draft.requirements.trim(),
    tech_keywords: parseDraftTerms(draft.keywords),
    capacity: Math.max(1, Number(draft.capacity.trim()) || 1),
    term_id: termId,
  };
}

export function buildPatchTopicRequest(draft: TeacherTopicDraft) {
  return {
    title: draft.title.trim(),
    summary: draft.summary.trim(),
    requirements: draft.requirements.trim(),
    tech_keywords: parseDraftTerms(draft.keywords),
    capacity: Math.max(1, Number(draft.capacity.trim()) || 1),
  };
}

export function mapStudentProfileToDraft(profile?: StudentProfile) {
  return {
    interests: profile?.interests?.join("，") ?? "",
    skills: profile?.skills?.join("，") ?? "",
    keywords: profile?.keywords?.join("，") ?? "",
    goal: profile?.goal ?? "",
    weeklyHours:
      typeof profile?.weeklyHours === "number" ? String(profile.weeklyHours) : "",
  };
}

export function buildStudentProfilePatch(
  draft: StudentProfileDraft,
): PatchUserMeRequest {
  const weeklyHours = Number(draft.weeklyHours.trim());

  return {
    student_profile: {
      interests: parseDraftTerms(draft.interests),
      skills: parseDraftTerms(draft.skills),
      keywords: parseDraftTerms(draft.keywords),
      goal: draft.goal.trim() || null,
      weekly_hours: Number.isFinite(weeklyHours) ? weeklyHours : null,
    },
  };
}
```

- [ ] **Step 4: Run the helper tests and verify they pass**

Run:

```bash
cd frontend
npx vitest run src/pages/topics/topics-page.utils.test.ts
```

Expected:

- All helper tests pass and the page now has reusable payload builders instead of local mock workbench logic.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/topics/topics-page.utils.ts frontend/src/pages/topics/topics-page.utils.test.ts
git commit -m "feat(frontend): add topics page form helpers"
```

### Task 3: Add Users API, Topics Mutations, And Status-Driven Polling

**Files:**
- Modify: `frontend/src/features/topics/topics.api.ts`
- Modify: `frontend/src/features/topics/topics.queries.ts`
- Create: `frontend/src/features/topics/topics.queries.test.ts`
- Create: `frontend/src/features/users/users.api.ts`
- Create: `frontend/src/features/users/users.queries.ts`
- Test: `frontend/src/features/topics/topics.queries.test.ts`

- [ ] **Step 1: Write the failing polling helper test**

```ts
// frontend/src/features/topics/topics.queries.test.ts
import { describe, expect, it } from "vitest";

import { getTopicPollingInterval } from "@/features/topics/topics.queries";

describe("topics.queries", () => {
  it("keeps polling while topic analysis is active", () => {
    expect(getTopicPollingInterval("pending")).toBe(2000);
    expect(getTopicPollingInterval("running")).toBe(2000);
  });

  it("stops polling after topic analysis reaches a terminal state", () => {
    expect(getTopicPollingInterval("done")).toBe(false);
    expect(getTopicPollingInterval("failed")).toBe(false);
    expect(getTopicPollingInterval(null)).toBe(false);
  });
});
```

- [ ] **Step 2: Run the polling helper test and verify it fails**

Run:

```bash
cd frontend
npx vitest run src/features/topics/topics.queries.test.ts
```

Expected:

- Test fails because `getTopicPollingInterval` does not exist yet.

- [ ] **Step 3: Implement the API wrappers and query hooks**

```ts
// frontend/src/features/topics/topics.api.ts
import { apiClient } from "@/lib/axios";
import type {
  PaginatedResponseDto,
  RecommendationTopicList,
  RecommendationTopicListDto,
  TopicDto,
} from "@/features/topics/topics.types";
import {
  mapPaginatedResponseDto,
  mapRecommendationTopicListDto,
  mapTopicDto,
} from "@/features/topics/topics.types";

export type CreateTopicPayload = {
  title: string;
  summary: string;
  requirements: string;
  tech_keywords: string[];
  capacity: number;
  term_id: string;
};

export type PatchTopicPayload = {
  title: string;
  summary: string;
  requirements: string;
  tech_keywords: string[];
  capacity: number;
};

export async function createTopic(payload: CreateTopicPayload) {
  const response = await apiClient.post<TopicDto>("/topics", payload);
  return mapTopicDto(response.data);
}

export async function updateTopic(topicId: string, payload: PatchTopicPayload) {
  const response = await apiClient.patch<TopicDto>(`/topics/${topicId}`, payload);
  return mapTopicDto(response.data);
}

export async function getTopicRecommendations(termId: string, topN = 10) {
  const response = await apiClient.get<RecommendationTopicListDto>(
    "/recommendations/topics",
    {
      params: {
        term_id: termId,
        top_n: topN,
        explain: true,
      },
    },
  );

  return mapRecommendationTopicListDto(response.data);
}
```

```ts
// frontend/src/features/users/users.api.ts
import { apiClient } from "@/lib/axios";
import type {
  PatchUserMeRequest,
  UserMeDto,
} from "@/features/users/users.types";
import { mapUserMeDto } from "@/features/users/users.types";

export async function getUserMe() {
  const response = await apiClient.get<UserMeDto>("/users/me");
  return mapUserMeDto(response.data);
}

export async function patchUserMe(payload: PatchUserMeRequest) {
  const response = await apiClient.patch<UserMeDto>("/users/me", payload);
  return mapUserMeDto(response.data);
}
```

```ts
// frontend/src/features/topics/topics.queries.ts
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  createTopic,
  getTopic,
  getTopicRecommendations,
  getTopics,
  updateTopic,
} from "@/features/topics/topics.api";
import type { AsyncStatus } from "@/types/app";
import type { Topic } from "@/features/topics/topics.types";

export function getTopicPollingInterval(status?: AsyncStatus | null) {
  return status === "pending" || status === "running" ? 2000 : false;
}

export const topicKeys = {
  all: ["topics"] as const,
  list: (termId: string) => [...topicKeys.all, "list", termId] as const,
  detail: (topicId: string) => [...topicKeys.all, "detail", topicId] as const,
  recommendations: (termId: string, topN: number) =>
    [...topicKeys.all, "recommendations", termId, topN] as const,
};

export function useTopicQuery(topicId: string | null, enabled: boolean) {
  return useQuery<Topic>({
    queryKey: topicId ? topicKeys.detail(topicId) : [...topicKeys.all, "detail", "empty"],
    queryFn: async () => getTopic(topicId!),
    enabled: enabled && Boolean(topicId),
    refetchInterval: (query) => getTopicPollingInterval(query.state.data?.llmKeywordJobStatus),
  });
}

export function useCreateTopicMutation() {
  return useMutation({
    mutationFn: createTopic,
  });
}

export function useUpdateTopicMutation() {
  return useMutation({
    mutationFn: ({ topicId, payload }: { topicId: string; payload: Parameters<typeof updateTopic>[1] }) =>
      updateTopic(topicId, payload),
  });
}

export function useTopicRecommendationsQuery(
  termId: string,
  topN: number,
  enabled: boolean,
) {
  return useQuery({
    queryKey: topicKeys.recommendations(termId, topN),
    queryFn: () => getTopicRecommendations(termId, topN),
    enabled,
  });
}
```

```ts
// frontend/src/features/users/users.queries.ts
import { useMutation, useQuery } from "@tanstack/react-query";

import { getUserMe, patchUserMe } from "@/features/users/users.api";

export const userKeys = {
  me: ["users", "me"] as const,
};

export function useUserMeQuery(enabled: boolean) {
  return useQuery({
    queryKey: userKeys.me,
    queryFn: getUserMe,
    enabled,
  });
}

export function useUpdateUserMeMutation() {
  return useMutation({
    mutationFn: patchUserMe,
  });
}
```

- [ ] **Step 4: Run the polling helper test and verify it passes**

Run:

```bash
cd frontend
npx vitest run src/features/topics/topics.queries.test.ts
```

Expected:

- `topics.queries.test.ts` passes and the polling rule matches the contract requirement to stop at terminal states.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/topics/topics.api.ts frontend/src/features/topics/topics.queries.ts frontend/src/features/topics/topics.queries.test.ts frontend/src/features/users/users.api.ts frontend/src/features/users/users.queries.ts
git commit -m "feat(frontend): add topics polling and users api layer"
```

### Task 4: Replace Teacher Demo Analysis With Real Topic Save And Portrait Rendering

**Files:**
- Modify: `frontend/src/pages/topics/topics-page.tsx`
- Create: `frontend/src/pages/topics/topics-page.test.tsx`
- Test: `frontend/src/pages/topics/topics-page.test.tsx`

- [ ] **Step 1: Write the failing teacher-mode page test**

```ts
// frontend/src/pages/topics/topics-page.test.tsx
import { StrictMode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const topic = {
  id: "topic-1",
  title: "AI 学术助手工作台",
  summary: "面向毕业设计的 AI 工作台",
  requirements: "熟悉 React、Flask 和异步任务",
  techKeywords: ["AI 助手", "异步任务"],
  capacity: 2,
  selectedCount: 1,
  teacherId: "teacher-1",
  termId: "term-2026-spring",
  status: "published",
  portrait: {
    keywords: ["画像", "推荐"],
    difficultyLabel: "advanced",
    difficultyReason: "跨前端、后端与异步任务",
    requiredCapabilities: ["React", "Flask"],
    suitableStudents: ["有项目经验的学生"],
    risks: ["范围较大"],
    summary: "这是一个适合答辩展示的综合题目。",
    extractedAt: "2026-05-09T00:00:00Z",
  },
  llmKeywordJobId: "job-1",
  llmKeywordJobStatus: "done",
  createdAt: "2026-05-09T00:00:00Z",
  updatedAt: "2026-05-09T00:00:00Z",
};

vi.mock("@/app/store", () => ({
  useAppStore: (selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      isAuthenticated: true,
      currentUser: {
        id: "teacher-1",
        username: "teacher-demo",
        role: "teacher",
        display_name: "演示教师",
      },
      currentTerm: {
        id: "term-2026-spring",
        name: "2026 春季学期",
      },
    }),
}));

vi.mock("@/features/topics/topics.queries", () => ({
  useTopicsQuery: () => ({
    data: { items: [topic], page: 1, pageSize: 50, total: 1 },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useTopicQuery: () => ({
    data: topic,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateTopicMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateTopicMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useTopicRecommendationsQuery: () => ({
    data: undefined,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/features/users/users.queries", () => ({
  useUserMeQuery: () => ({
    data: undefined,
    isLoading: false,
    isError: false,
  }),
  useUpdateUserMeMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

describe("TopicsPage teacher mode", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  it("renders backend portrait summary in teacher mode", async () => {
    const { TopicsPage } = await import("@/pages/topics/topics-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <TopicsPage />
        </StrictMode>,
      );
    });

    const teacherButton = Array.from(container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("老师分析"),
    );

    teacherButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(container.textContent).toContain("这是一个适合答辩展示的综合题目。");
    expect(container.textContent).toContain("跨前端、后端与异步任务");
  });
});
```

- [ ] **Step 2: Run the teacher-mode page test and verify it fails**

Run:

```bash
cd frontend
npx vitest run src/pages/topics/topics-page.test.tsx
```

Expected:

- Test fails because the current page still renders `buildTopicAnalysis()` demo output instead of backend portrait data.

- [ ] **Step 3: Implement the teacher-mode real integration**

```tsx
// frontend/src/pages/topics/topics-page.tsx
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import {
  useCreateTopicMutation,
  useTopicQuery,
  useTopicRecommendationsQuery,
  useTopicsQuery,
  useUpdateTopicMutation,
  topicKeys,
} from "@/features/topics/topics.queries";
import {
  buildCreateTopicRequest,
  buildPatchTopicRequest,
  type StudentProfileDraft,
  type TeacherTopicDraft,
} from "@/pages/topics/topics-page.utils";

const initialTeacherDraft: TeacherTopicDraft = {
  title: "",
  summary: "",
  requirements: "",
  keywords: "",
  capacity: "2",
};

function formatJobStatusLabel(
  status?: "pending" | "running" | "done" | "failed" | null,
) {
  switch (status) {
    case "pending":
      return "题目画像待分析";
    case "running":
      return "题目画像分析中";
    case "done":
      return "题目画像已完成";
    case "failed":
      return "题目画像分析失败";
    default:
      return "";
  }
}

const queryClient = useQueryClient();
const currentUser = useAppStore((state) => state.currentUser);
const isTeacher = currentUser?.role === "teacher" || currentUser?.role === "admin";
const createTopicMutation = useCreateTopicMutation();
const updateTopicMutation = useUpdateTopicMutation();

async function handleSaveTeacherDraft() {
  if (!isTeacher) {
    return;
  }

  const savedTopic = selectedTopic?.teacherId === currentUser?.id
    ? await updateTopicMutation.mutateAsync({
        topicId: selectedTopic.id,
        payload: buildPatchTopicRequest(teacherDraft),
      })
    : await createTopicMutation.mutateAsync(
        buildCreateTopicRequest(teacherDraft, currentTerm.id),
      );

  setSelectedTopicId(savedTopic.id);

  await queryClient.invalidateQueries({ queryKey: topicKeys.list(currentTerm.id) });
  await queryClient.invalidateQueries({ queryKey: topicKeys.detail(savedTopic.id) });
}

const teacherPortrait = selectedTopic?.portrait;
const teacherStatusLabel = formatJobStatusLabel(selectedTopic?.llmKeywordJobStatus);
```

```tsx
// frontend/src/pages/topics/topics-page.tsx
{mode === "teacher" ? (
  <div className="topics-layout">
    <PageSection className="paper">
      <SectionHeading
        title="老师输入题目"
        description="保存后触发后端题目画像分析，并在右侧展示结构化分析结果。"
      />

      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 18 }}>
        <Button
          variant="outline"
          onClick={() => selectedTopic && syncTeacherDraftFromTopic(selectedTopic)}
          disabled={!selectedTopic}
        >
          导入当前选中题目
        </Button>
        <Button
          onClick={handleSaveTeacherDraft}
          disabled={!isTeacher || createTopicMutation.isPending || updateTopicMutation.isPending}
        >
          保存并生成分析
        </Button>
      </div>
    </PageSection>

    <PageSection className="paper">
      <SectionHeading
        title="题目画像结果"
        description="结果来自题目详情接口返回的 portrait 字段，而不是本地演示函数。"
      />

      {teacherStatusLabel ? (
        <div className="detail-card" style={{ marginTop: 18 }}>
          <p style={{ fontWeight: 600 }}>分析状态</p>
          <p className="muted small" style={{ marginTop: 12 }}>{teacherStatusLabel}</p>
        </div>
      ) : null}

      {teacherPortrait ? (
        <>
          <div className="detail-card" style={{ marginTop: 18 }}>
            <p style={{ fontWeight: 600 }}>AI 分析摘要</p>
            <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
              {teacherPortrait.summary || "暂无题目画像摘要。"}
            </p>
          </div>
          <div className="detail-card" style={{ marginTop: 18 }}>
            <p style={{ fontWeight: 600 }}>难度判断</p>
            <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
              {teacherPortrait.difficultyLabel || "未标注"} · {teacherPortrait.difficultyReason || "暂无说明"}
            </p>
          </div>
          <div className="detail-card" style={{ marginTop: 18 }}>
            <p style={{ fontWeight: 600 }}>所需能力</p>
            <div className="keyword-row" style={{ marginTop: 12 }}>
              {teacherPortrait.requiredCapabilities.map((item) => (
                <span key={item} className="keyword-pill">{item}</span>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div style={{ marginTop: 22 }}>
          <EmptyState
            title="等待题目画像"
            description="保存教师题目后，这里会展示后端异步生成的结构化画像。"
          />
        </div>
      )}
    </PageSection>
  </div>
) : null}
```

- [ ] **Step 4: Run the teacher-mode page test and verify it passes**

Run:

```bash
cd frontend
npx vitest run src/pages/topics/topics-page.test.tsx
```

Expected:

- Teacher-mode smoke test passes and confirms the page reads portrait content from real detail data.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/topics/topics-page.tsx frontend/src/pages/topics/topics-page.test.tsx
git commit -m "feat(frontend): connect teacher topics analysis flow"
```

### Task 5: Add Student Profile Persistence And Real Recommendation Rendering

**Files:**
- Modify: `frontend/src/pages/topics/topics-page.tsx`
- Modify: `frontend/src/pages/topics/topics-page.test.tsx`
- Delete: `frontend/src/features/topics/topics-workbench.ts`
- Delete: `frontend/src/features/topics/topics-workbench.test.ts`
- Test: `frontend/src/pages/topics/topics-page.test.tsx`

- [ ] **Step 1: Extend the page test with a failing student recommendation case**

```ts
// frontend/src/pages/topics/topics-page.test.tsx
const recommendationData = {
  topN: 10,
  items: [
    {
      topicId: "topic-1",
      title: "AI 学术助手工作台",
      score: 92,
      explain: {
        matchedSkills: ["React"],
        matchedKeywords: ["异步任务"],
        matchedCapabilities: ["前端实现", "任务编排"],
        difficultyFit: "每周 8-10 小时可以覆盖题目推进节奏",
        capacityStatus: "available",
        warnings: ["仍需补足推荐解释模块"],
        reasons: ["题目画像与学生画像高度重合"],
      },
    },
  ],
};

vi.mock("@/features/users/users.queries", () => ({
  useUserMeQuery: () => ({
    data: {
      id: "user-1",
      username: "student-demo",
      role: "student",
      displayName: "联调学生",
      email: "student@example.com",
      studentProfile: {
        interests: ["AI 学术助手", "选题推荐"],
        skills: ["React", "Flask"],
        keywords: ["画像"],
        goal: "做一个适合答辩展示的系统",
        weeklyHours: 8,
      },
      teacherProfile: null,
    },
    isLoading: false,
    isError: false,
  }),
  useUpdateUserMeMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("@/features/topics/topics.queries", () => ({
  useTopicsQuery: () => ({
    data: { items: [topic], page: 1, pageSize: 50, total: 1 },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useTopicQuery: () => ({
    data: topic,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateTopicMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateTopicMutation: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useTopicRecommendationsQuery: () => ({
    data: recommendationData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

it("hydrates student profile and renders backend recommendation explanations", async () => {
  const { TopicsPage } = await import("@/pages/topics/topics-page");
  const root = createRoot(container);

  await act(async () => {
    root.render(
      <StrictMode>
        <TopicsPage />
      </StrictMode>,
    );
  });

  const studentButton = Array.from(container.querySelectorAll("button")).find((button) =>
    button.textContent?.includes("学生推荐"),
  );

  studentButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));

  expect(container.textContent).toContain("AI 学术助手工作台");
  expect(container.textContent).toContain("每周 8-10 小时可以覆盖题目推进节奏");
  expect(container.textContent).toContain("题目画像与学生画像高度重合");
});
```

- [ ] **Step 2: Run the student recommendation page test and verify it fails**

Run:

```bash
cd frontend
npx vitest run src/pages/topics/topics-page.test.tsx
```

Expected:

- Test fails because the current student mode still uses local recommendation results and does not hydrate from `/users/me`.

- [ ] **Step 3: Implement student persistence, recommendation rendering, and mock cleanup**

```tsx
// frontend/src/pages/topics/topics-page.tsx
import { useUserMeQuery, useUpdateUserMeMutation } from "@/features/users/users.queries";
import {
  buildStudentProfilePatch,
  mapStudentProfileToDraft,
  type StudentProfileDraft,
} from "@/pages/topics/topics-page.utils";

const initialStudentDraft: StudentProfileDraft = {
  interests: "",
  skills: "",
  keywords: "",
  goal: "",
  weeklyHours: "",
};

const [studentDraft, setStudentDraft] = useState<StudentProfileDraft>(initialStudentDraft);
const [studentDraftDirty, setStudentDraftDirty] = useState(false);
const [recommendationEnabled, setRecommendationEnabled] = useState(false);

const userMeQuery = useUserMeQuery(isAuthenticated && mode === "student");
const updateUserMeMutation = useUpdateUserMeMutation();
const recommendationsQuery = useTopicRecommendationsQuery(
  currentTerm.id,
  10,
  isAuthenticated && mode === "student" && recommendationEnabled,
);

useEffect(() => {
  if (mode !== "student" || studentDraftDirty) {
    return;
  }

  if (userMeQuery.data?.studentProfile) {
    setStudentDraft(mapStudentProfileToDraft(userMeQuery.data.studentProfile));
  }
}, [mode, studentDraftDirty, userMeQuery.data?.studentProfile]);

async function handleSaveAndRecommend() {
  await updateUserMeMutation.mutateAsync(buildStudentProfilePatch(studentDraft));
  setRecommendationEnabled(true);
  await recommendationsQuery.refetch();
}
```

```tsx
// frontend/src/pages/topics/topics-page.tsx
{mode === "student" ? (
  <div className="topics-layout">
    <PageSection className="paper">
      <SectionHeading
        title="学生画像输入"
        description="先保存学生画像，再从后端获取推荐结果和解释字段。"
      />

      <div className="form-stack">
        <div className="field">
          <label htmlFor="student-interests">兴趣方向</label>
          <Textarea
            id="student-interests"
            value={studentDraft.interests}
            onChange={(event) => {
              setStudentDraftDirty(true);
              setStudentDraft((current) => ({ ...current, interests: event.target.value }));
            }}
          />
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 18 }}>
        <Button
          onClick={handleSaveAndRecommend}
          disabled={updateUserMeMutation.isPending}
        >
          保存画像并开始推荐
        </Button>
      </div>
    </PageSection>

    <PageSection className="paper">
      <SectionHeading
        title="推荐结果"
        description="结果来自 `/recommendations/topics`，解释字段与论文逻辑保持一致。"
      />

      {recommendationsQuery.data?.items.length ? (
        <div className="topic-list">
          {recommendationsQuery.data.items.map((item) => (
            <div key={item.topicId} className="topic-card">
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <div>
                  <h3 className="topic-title">{item.title}</h3>
                  <p className="muted small" style={{ marginTop: 10 }}>推荐分：{item.score}</p>
                </div>
                <span className="badge">{item.explain?.capacityStatus || "available"}</span>
              </div>
              <div className="keyword-row">
                {(item.explain?.matchedCapabilities ?? []).map((capability) => (
                  <span key={capability} className="keyword-pill">{capability}</span>
                ))}
              </div>
              <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                {item.explain?.difficultyFit || "暂无难度匹配说明。"}
              </p>
              <ul className="summary-points" style={{ marginTop: 12, paddingLeft: 0 }}>
                {(item.explain?.reasons ?? []).map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
              {(item.explain?.warnings ?? []).length ? (
                <p className="muted small" style={{ marginTop: 12 }}>
                  {(item.explain?.warnings ?? []).join("；")}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <div style={{ marginTop: 22 }}>
          <EmptyState
            title="等待生成推荐"
            description="保存学生画像后，这里会显示真实推荐结果。"
          />
        </div>
      )}
    </PageSection>
  </div>
) : null}
```

```bash
git rm frontend/src/features/topics/topics-workbench.ts frontend/src/features/topics/topics-workbench.test.ts
```

- [ ] **Step 4: Run the full frontend verification for this feature**

Run:

```bash
cd frontend
npx vitest run src/features/topics/topics.utils.test.ts src/features/users/users.types.test.ts src/pages/topics/topics-page.utils.test.ts src/features/topics/topics.queries.test.ts src/pages/topics/topics-page.test.tsx
npm run lint
npm run build
```

Expected:

- All listed frontend tests pass.
- ESLint exits with code `0`.
- Vite build exits with code `0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/topics/topics-page.tsx frontend/src/pages/topics/topics-page.test.tsx frontend/src/features/topics/topics.utils.test.ts frontend/src/features/topics/topics.queries.ts frontend/src/features/topics/topics.api.ts frontend/src/features/topics/topics.types.ts frontend/src/features/users/users.types.ts frontend/src/features/users/users.api.ts frontend/src/features/users/users.queries.ts frontend/src/pages/topics/topics-page.utils.ts frontend/src/pages/topics/topics-page.utils.test.ts
git add -u frontend/src/features/topics/topics-workbench.ts frontend/src/features/topics/topics-workbench.test.ts
git commit -m "feat(frontend): connect topics analysis and recommendation flows"
```

## Self-Review

### Spec coverage

- Browse mode remains in `/app/topics`: covered by Task 4 page refactor.
- Teacher save/update via `/topics`: covered by Task 3 API layer and Task 4 page integration.
- Portrait polling until terminal state: covered by Task 3 polling helper and `useTopicQuery`.
- Student profile persistence via `/users/me`: covered by Task 1 model mapping, Task 3 users API layer, and Task 5 page integration.
- Recommendation results via `/recommendations/topics`: covered by Task 1 mapping, Task 3 API/query layer, and Task 5 rendering.
- Remove local demo workbench logic: covered by Task 5 cleanup.

### Placeholder scan

- No `TODO`, `TBD`, or deferred implementation markers remain.
- Each task includes exact file paths, commands, and concrete code snippets.

### Type consistency

- `Topic.portrait` uses camelCase in the frontend and snake_case in DTO types.
- `StudentProfile.weeklyHours` maps to `weekly_hours` in request DTOs.
- Recommendation explain fields stay aligned with `contract.yaml`.

