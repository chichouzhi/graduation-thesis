import { StrictMode } from "react";
import type { ReactNode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

vi.mock("react-router-dom", () => ({
  Link: ({ to, children, className }: { to: string; children: ReactNode; className?: string }) => (
    <a href={to} className={className}>
      {children}
    </a>
  ),
}));

const conversations = {
  items: [
    {
      id: "conversation-1",
      term_id: "term-1",
      title: "选题咨询",
      context_type: "topic",
      created_at: "2026-05-01T08:00:00Z",
      updated_at: "2026-05-01T09:00:00Z",
    },
  ],
  page: 1,
  pageSize: 50,
  total: 1,
};

const documents = {
  items: [
    {
      id: "doc-1",
      termId: "term-1",
      status: "running",
      filename: "论文初稿.pdf",
      currentStage: "pdf_extract",
      progress: { completedChunks: 2, totalChunks: 8 },
      taskType: "summary",
      createdAt: "2026-05-02T08:00:00Z",
      updatedAt: "2026-05-05T10:00:00Z",
      retryCount: 0,
      resultPreview: "正在提取 PDF 内容",
    },
  ],
  page: 1,
  pageSize: 50,
  total: 1,
};

const milestones = {
  items: [
    {
      id: "mile-1",
      studentId: "student-1",
      title: "完成系统联调",
      description: "整理前后端真实接口验证记录",
      startDate: "2026-05-01",
      endDate: "2026-05-09",
      status: "doing",
      sortOrder: 1,
      isOverdue: false,
      createdAt: "2026-05-01T00:00:00Z",
      updatedAt: "2026-05-06T10:00:00Z",
    },
  ],
  page: 1,
  pageSize: 50,
  total: 1,
};

const topics = {
  items: [
    {
      id: "topic-1",
      title: "AI 学术助手工作台",
      summary: "面向毕业设计的 AI 工作台",
      requirements: "熟悉 React、Flask 和异步任务",
      techKeywords: ["AI 助手", "异步任务"],
      capacity: 2,
      selectedCount: 1,
      teacherId: "teacher-1",
      termId: "term-1",
      status: "published",
      portrait: {
        keywords: ["画像", "推荐"],
        difficultyLabel: "advanced",
        difficultyReason: "跨前端、后端与异步任务",
        requiredCapabilities: ["React", "Flask"],
        suitableStudents: ["有项目经验的学生"],
        risks: ["范围较大"],
        summary: "这是一个适合答辩展示的综合题目。",
        extractedAt: "2026-05-04T00:00:00Z",
      },
      llmKeywordJobId: "job-1",
      llmKeywordJobStatus: "done",
      createdAt: "2026-05-01T00:00:00Z",
      updatedAt: "2026-05-06T12:00:00Z",
    },
    {
      id: "topic-2",
      title: "选题推荐分析",
      summary: "帮助学生进行选题推荐",
      requirements: "理解推荐逻辑",
      techKeywords: ["推荐", "画像"],
      capacity: 2,
      selectedCount: 0,
      teacherId: "teacher-1",
      termId: "term-1",
      status: "draft",
      portrait: null,
      llmKeywordJobId: "job-2",
      llmKeywordJobStatus: "running",
      createdAt: "2026-05-02T00:00:00Z",
      updatedAt: "2026-05-05T12:00:00Z",
    },
  ],
  page: 1,
  pageSize: 50,
  total: 2,
};

const assignments = {
  items: [
    {
      id: "assignment-1",
      studentId: "student-1",
      studentName: "联调学生",
      teacherId: "teacher-1",
      topicId: "topic-1",
      topicTitle: "AI 学术助手工作台",
      termId: "term-1",
      applicationId: "application-1",
      status: "active",
      confirmedAt: "2026-05-09T03:00:00Z",
    },
  ],
  page: 1,
  pageSize: 50,
  total: 1,
};

vi.mock("@/app/store", () => ({
  useAppStore: (selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      isAuthenticated: true,
      currentUser: {
        id: "student-1",
        username: "student-demo",
        role: "student",
        display_name: "联调学生",
      },
      currentTerm: {
        id: "term-1",
        name: "2026 春季学期",
      },
    }),
}));

vi.mock("@/features/chat/chat.queries", () => ({
  useConversationsQuery: () => ({
    data: conversations,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/features/documents/documents.queries", () => ({
  useDocumentTasksQuery: () => ({
    data: documents,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/features/taskboard/taskboard.queries", () => ({
  useMilestonesQuery: () => ({
    data: milestones,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/features/topics/topics.queries", () => ({
  useTopicsQuery: () => ({
    data: topics,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/features/selection/selection.queries", () => ({
  useAssignmentsQuery: () => ({
    data: assignments,
    isLoading: false,
    isError: false,
  }),
}));

describe("DashboardPage", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  it("renders aggregated workspace overview from existing queries", async () => {
    const { DashboardPage } = await import("@/pages/dashboard/dashboard-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <DashboardPage />
        </StrictMode>,
      );
    });

    expect(container.textContent).toContain("AI 学术助手工作台");
    expect(container.textContent).toContain("当前重点");
    expect(container.textContent).toContain("题目画像");
    expect(container.textContent).toContain("论文初稿.pdf");
    expect(container.textContent).toContain("选题咨询");
    expect(container.textContent).toContain("AI 学术助手工作台");
    expect(container.textContent).toContain("指导关系");
    expect(container.textContent).toContain("联调学生");
    expect(container.textContent).toContain("已确认指导");
    expect(container.textContent).toContain("答辩演示链路");
    expect(container.textContent).toContain("保存学生画像并生成推荐");
    expect(container.textContent).toContain("查看推荐理由并提交志愿");
    expect(container.textContent).toContain("等待教师确认形成指导关系");
    expect(container.textContent).toContain("进入任务看板持续推进毕业设计");
  });

  it("keeps the dashboard defense flow focused on the student workflow", async () => {
    const { DashboardPage } = await import("@/pages/dashboard/dashboard-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <DashboardPage />
        </StrictMode>,
      );
    });

    expect(container.textContent).toContain("保存学生画像并生成推荐");
    expect(container.textContent).toContain("查看推荐理由并提交志愿");
    expect(container.textContent).toContain("进入任务看板持续推进毕业设计");
    expect(container.textContent).not.toContain("老师录入选题并生成题目画像");
  });
});
