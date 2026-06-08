import { StrictMode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

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

const recommendation = {
  topicId: "topic-1",
  title: "AI 学术助手工作台",
  score: 96,
  explain: {
    matchedSkills: ["React", "Flask"],
    matchedKeywords: ["画像", "推荐"],
    matchedCapabilities: ["前后端联调", "异步任务"],
    difficultyFit: "与你的技能和时间投入较匹配，适合作为答辩型题目。",
    capacityStatus: "available",
    warnings: [],
    reasons: ["和学生画像中的前端联调、异步任务经验高度一致。"],
  },
};

const topicsListResponse = { items: [topic], page: 1, pageSize: 50, total: 1 };
const studentProfile = {
  interests: ["AI 学术助手", "选题推荐"],
  skills: ["React", "Flask"],
  keywords: ["画像", "异步任务"],
  goal: "希望完成可用于答辩演示的毕业设计",
  weeklyHours: 10,
};
const userMe = {
  id: "student-1",
  username: "student-demo",
  role: "student",
  displayName: "联调学生",
  email: "student@example.com",
  studentProfile,
  teacherProfile: null,
};
const recommendationList = { items: [recommendation], topN: 10 };

const appStoreState = vi.hoisted(() => ({
  currentRole: "teacher" as "student" | "teacher" | "admin",
}));

const selectionMockState = vi.hoisted(() => ({
  studentApplications: [] as Array<{
    id: string;
    topicId: string;
    topicTitle: string;
    studentId: string;
    termId: string;
    priority: 1 | 2;
    status: "pending" | "withdrawn" | "accepted" | "rejected" | "superseded";
    createdAt: string;
    updatedAt: string;
  }>,
  teacherApplications: [
    {
      id: "application-1",
      topicId: "topic-1",
      topicTitle: "AI 学术助手工作台",
      studentId: "student-1",
      termId: "term-2026-spring",
      priority: 1,
      status: "pending",
      createdAt: "2026-05-09T00:00:00Z",
      updatedAt: "2026-05-09T01:00:00Z",
    },
  ] as Array<{
    id: string;
    topicId: string;
    topicTitle: string;
    studentId: string;
    termId: string;
    priority: 1 | 2;
    status: "pending" | "withdrawn" | "accepted" | "rejected" | "superseded";
    createdAt: string;
    updatedAt: string;
  }>,
}));

vi.mock("@/app/store", () => ({
  useAppStore: (selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      isAuthenticated: true,
      currentUser: {
        id: "teacher-1",
        username: "teacher-demo",
        role: appStoreState.currentRole,
        display_name: "演示教师",
      },
      currentTerm: {
        id: "term-2026-spring",
        name: "2026 春季学期",
      },
    }),
}));

const updateUserMeMutation = vi.fn().mockResolvedValue({});
const createApplicationMutation = vi.fn().mockResolvedValue({});
const deleteApplicationMutation = vi.fn().mockResolvedValue(undefined);
const decideApplicationMutation = vi.fn().mockResolvedValue({});
const recommendationsRefetch = vi.fn();

vi.mock("@/features/topics/topics.queries", () => ({
  useTopicsQuery: () => ({
    data: topicsListResponse,
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
    data: recommendationList,
    isLoading: false,
    isError: false,
    refetch: recommendationsRefetch,
  }),
}));

vi.mock("@/features/users/users.queries", () => ({
  useUserMeQuery: () => ({
    data: userMe,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useUpdateUserMeMutation: () => ({
    mutateAsync: updateUserMeMutation,
    isPending: false,
  }),
}));

vi.mock("@/features/selection/selection.queries", () => ({
  useApplicationsQuery: (_enabled: boolean, params?: { topicId?: string }) => ({
    data: {
      items: params?.topicId ? selectionMockState.teacherApplications : selectionMockState.studentApplications,
      page: 1,
      pageSize: 50,
      total: params?.topicId
        ? selectionMockState.teacherApplications.length
        : selectionMockState.studentApplications.length,
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateApplicationMutation: () => ({
    mutateAsync: createApplicationMutation,
    isPending: false,
  }),
  useDeleteApplicationMutation: () => ({
    mutateAsync: deleteApplicationMutation,
    isPending: false,
  }),
  useDecideApplicationMutation: () => ({
    mutateAsync: decideApplicationMutation,
    isPending: false,
  }),
}));

describe("TopicsPage", () => {
  let container: HTMLDivElement;

  function renderTopicsPage() {
    return import("@/pages/topics/topics-page").then(({ TopicsPage }) => {
      const root = createRoot(container);

      return act(async () => {
        root.render(
          <StrictMode>
            <TopicsPage />
          </StrictMode>,
        );
      });
    });
  }

  beforeEach(() => {
    appStoreState.currentRole = "teacher";
    selectionMockState.studentApplications = [];
    selectionMockState.teacherApplications = [
      {
        id: "application-1",
        topicId: "topic-1",
        topicTitle: "AI 学术助手工作台",
        studentId: "student-1",
        termId: "term-2026-spring",
        priority: 1,
        status: "pending",
        createdAt: "2026-05-09T00:00:00Z",
        updatedAt: "2026-05-09T01:00:00Z",
      },
    ];
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  it("renders teacher workspace by default for teacher users", async () => {
    appStoreState.currentRole = "teacher";
    await renderTopicsPage();

    expect(container.textContent).toContain("老师输入题目");
    expect(container.textContent).toContain("这是一个适合答辩展示的综合题目。");
    expect(container.textContent).toContain("跨前端、后端与异步任务");
  });

  it("renders student workspace by default for student users", async () => {
    appStoreState.currentRole = "student";
    await renderTopicsPage();

    expect(container.textContent).toContain("学生画像输入");
    expect(container.textContent).toContain("保存画像并开始推荐");
    expect(container.textContent).not.toContain("当前只展示题目浏览工作区");
  });

  it("shows an application button in browse mode for admin users", async () => {
    appStoreState.currentRole = "admin";
    await renderTopicsPage();

    const applyButton = Array.from(container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("申请第一志愿"),
    );

    expect(applyButton).toBeTruthy();

    await act(async () => {
      applyButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(createApplicationMutation).toHaveBeenCalledWith({
      topic_id: "topic-1",
      term_id: "term-2026-spring",
      priority: 1,
    });
  });

  it("accepts a pending application in teacher mode", async () => {
    appStoreState.currentRole = "teacher";
    await renderTopicsPage();

    expect(container.textContent).toContain("学生志愿");
    expect(container.textContent).toContain("student-1");

    const acceptButton = Array.from(container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("接受志愿"),
    );

    await act(async () => {
      acceptButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(decideApplicationMutation).toHaveBeenCalledWith({
      applicationId: "application-1",
      payload: { action: "accept" },
    });
  });

  it("does not show withdraw actions for non-pending student applications", async () => {
    appStoreState.currentRole = "student";
    selectionMockState.studentApplications = [
      {
        id: "application-2",
        topicId: "topic-1",
        topicTitle: "AI 学术助手工作台",
        studentId: "student-1",
        termId: "term-2026-spring",
        priority: 2,
        status: "accepted",
        createdAt: "2026-05-09T00:00:00Z",
        updatedAt: "2026-05-09T01:00:00Z",
      },
    ];

    await renderTopicsPage();

    expect(container.textContent).toContain("第 2 志愿 · 已接受");
    expect(container.textContent).not.toContain("撤销当前志愿");

    const withdrawButtons = Array.from(container.querySelectorAll("button")).filter((button) =>
      button.textContent?.includes("撤销"),
    );

    expect(withdrawButtons).toHaveLength(0);
    expect(deleteApplicationMutation).not.toHaveBeenCalled();
  });
});
