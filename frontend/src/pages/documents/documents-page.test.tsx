import { StrictMode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

const selectedTask = {
  id: "document-task-1",
  filename: "毕业设计开题报告.pdf",
  taskType: "summary",
  language: "zh",
  status: "running",
  currentStage: "pdf_extract",
  progress: 0.42,
  resultPreview: "正在提取 PDF 内容",
  result: null,
  errorCode: null,
  errorMessage: null,
  createdAt: "2026-05-09T00:00:00Z",
  updatedAt: "2026-05-09T00:10:00Z",
};

let tasksResponse = {
  items: [selectedTask],
  page: 1,
  pageSize: 50,
  total: 1,
};

const pollingCalls: Array<string | null> = [];

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
        id: "term-2026-spring",
        name: "2026 春季学期",
      },
    }),
}));

vi.mock("@/features/documents/documents.queries", () => ({
  useDocumentTasksQuery: () => ({
    data: tasksResponse,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useUploadDocumentTaskMutation: () => ({
    mutate: vi.fn(),
    isPending: false,
    data: undefined,
  }),
  usePollingDocumentTaskQuery: (taskId: string | null) => ({
    data: taskId === selectedTask.id ? selectedTask : undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    __taskId: pollingCalls.push(taskId),
  }),
}));

describe("DocumentsPage", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    tasksResponse = {
      items: [selectedTask],
      page: 1,
      pageSize: 50,
      total: 1,
    };
    pollingCalls.length = 0;
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("keeps the current document selection when the task list temporarily becomes empty", async () => {
    const { DocumentsPage } = await import("@/pages/documents/documents-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <DocumentsPage />
        </StrictMode>,
      );
    });

    await act(async () => {
      await Promise.resolve();
    });

    expect(pollingCalls.at(-1)).toBe("document-task-1");

    tasksResponse = {
      items: [],
      page: 1,
      pageSize: 50,
      total: 0,
    };

    await act(async () => {
      root.render(
        <StrictMode>
          <DocumentsPage />
        </StrictMode>,
      );
    });

    await act(async () => {
      await Promise.resolve();
    });

    expect(pollingCalls.at(-1)).toBe("document-task-1");

    await act(async () => {
      root.unmount();
    });
  });
});
