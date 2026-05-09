import { StrictMode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

const milestone = {
  id: "milestone-1",
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
};

const createMilestone = vi.fn().mockResolvedValue(milestone);
const updateMilestone = vi.fn().mockResolvedValue({ ...milestone, status: "done" });
const deleteMilestone = vi.fn().mockResolvedValue(undefined);
const useMilestonesQueryMock = vi.fn();

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

function fillInput(input: HTMLInputElement, value: string) {
  const valueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  valueSetter?.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

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

vi.mock("@/features/taskboard/taskboard.queries", () => ({
  useMilestonesQuery: (enabled: boolean, params?: { studentId?: string }) => {
    useMilestonesQueryMock(enabled, params);

    return {
      data: { items: [milestone], page: 1, pageSize: 50, total: 1 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    };
  },
  useCreateMilestoneMutation: () => ({
    mutateAsync: createMilestone,
    isPending: false,
  }),
  useUpdateMilestoneMutation: () => ({
    mutateAsync: updateMilestone,
    isPending: false,
  }),
  useDeleteMilestoneMutation: () => ({
    mutateAsync: deleteMilestone,
    isPending: false,
  }),
}));

vi.mock("@/features/selection/selection.queries", () => ({
  useAssignmentsQuery: () => ({
    data: assignments,
    isLoading: false,
    isError: false,
  }),
}));

describe("TaskboardPage", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  it("creates a milestone from the form", async () => {
    const { TaskboardPage } = await import("@/pages/taskboard/taskboard-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <TaskboardPage />
        </StrictMode>,
      );
    });

    await act(async () => {
      fillInput(container.querySelector<HTMLInputElement>("#milestone-title")!, "补充答辩材料");
      fillInput(container.querySelector<HTMLInputElement>("#milestone-end-date")!, "2026-05-12");
    });

    const createButton = Array.from(container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("创建里程碑"),
    );

    await act(async () => {
      createButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(createMilestone).toHaveBeenCalledWith({
      title: "补充答辩材料",
      description: null,
      start_date: "",
      end_date: "2026-05-12",
      status: "todo",
      sort_order: 0,
    });
  });

  it("loads milestones for the selected guidance assignment student", async () => {
    const { TaskboardPage } = await import("@/pages/taskboard/taskboard-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <TaskboardPage />
        </StrictMode>,
      );
    });

    expect(container.textContent).toContain("指导课题");
    expect(container.textContent).toContain("AI 学术助手工作台");
    expect(container.textContent).toContain("联调学生");
    expect(useMilestonesQueryMock).toHaveBeenCalledWith(true, {
      studentId: "student-1",
    });
  });

  it("updates status and deletes milestone from card actions", async () => {
    const { TaskboardPage } = await import("@/pages/taskboard/taskboard-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <TaskboardPage />
        </StrictMode>,
      );
    });

    const doneButton = Array.from(container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("标记完成"),
    );
    const deleteButton = Array.from(container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("删除"),
    );

    await act(async () => {
      doneButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    await act(async () => {
      deleteButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(updateMilestone).toHaveBeenCalledWith({
      milestoneId: "milestone-1",
      payload: { status: "done" },
    });
    expect(deleteMilestone).toHaveBeenCalledWith("milestone-1");
  });
});
