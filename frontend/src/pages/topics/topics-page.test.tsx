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

    await act(async () => {
      teacherButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(container.textContent).toContain("这是一个适合答辩展示的综合题目。");
    expect(container.textContent).toContain("跨前端、后端与异步任务");
  });
});
