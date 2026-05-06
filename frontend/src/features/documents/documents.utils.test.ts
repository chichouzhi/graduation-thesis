import { describe, expect, expectTypeOf, it } from "vitest";

import {
  buildDocumentSummary,
  getDocumentProgressLabel,
  isDocumentTaskTerminal,
  shouldPollDocumentTask,
} from "@/features/documents/documents.utils";
import type {
  DocumentTask,
  DocumentTaskDto,
  DocumentTaskListItem,
  DocumentTaskListItemDto,
  DocumentSummaryView,
  DocumentTaskProgressView,
  PaginatedResponse,
  PaginatedResponseDto,
} from "@/features/documents/documents.types";
import {
  mapDocumentTaskDto,
  mapDocumentTaskListItemDto,
  mapPaginatedResponseDto,
} from "@/features/documents/documents.types";

const baseTaskDto: DocumentTaskDto = {
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

const baseProgressView: DocumentTaskProgressView = {
  completedChunks: 1,
  totalChunks: 3,
};

const baseTaskListItemDto: DocumentTaskListItemDto = {
  id: "task-1",
  term_id: "term-1",
  status: "running",
  filename: "paper.pdf",
  current_stage: "summarize_chunks",
  progress: { completed_chunks: 1, total_chunks: 3 },
  task_type: "summary",
  created_at: "2026-05-06T00:00:00Z",
  updated_at: "2026-05-06T00:00:00Z",
  retry_count: 0,
  result_preview: "summary text",
};

const baseSummaryView: DocumentSummaryView = {
  summary: "summary text",
  bulletPoints: ["point-a", "point-b"],
};

describe("documents.utils", () => {
  it("keeps DTO and helper-facing view types distinct", () => {
    expectTypeOf(baseTaskDto.progress).toEqualTypeOf<
      DocumentTaskDto["progress"] | undefined
    >();
    expectTypeOf<DocumentTask["termId"]>().toEqualTypeOf<string>();
    expectTypeOf<DocumentTaskProgressView>().toEqualTypeOf<{
      completedChunks?: number;
      totalChunks?: number;
    }>();
    expectTypeOf<DocumentSummaryView>().toEqualTypeOf<{
      summary: string;
      bulletPoints: string[];
    }>();
  });

  it("maps document task DTOs into frontend-facing models", () => {
    const task = mapDocumentTaskDto(baseTaskDto);

    expect(task).toEqual({
      id: "task-1",
      termId: "term-1",
      status: "running",
      filename: "paper.pdf",
      taskType: "summary",
      language: "zh",
      currentStage: "summarize_chunks",
      progress: {
        completedChunks: 1,
        totalChunks: 3,
      },
      artifacts: [],
      lockedAt: undefined,
      lastCompletedChunk: undefined,
      createdAt: "2026-05-06T00:00:00Z",
      updatedAt: "2026-05-06T00:00:00Z",
      result: {
        summary: "summary text",
        bulletPoints: ["point-a", "point-b"],
        rawModel: "gpt",
      },
      resultStorageUri: undefined,
      errorCode: undefined,
      errorMessage: undefined,
      retryCount: 0,
      maxAttempts: undefined,
      nextRetryAt: undefined,
    });
    expect(task).not.toHaveProperty("term_id");
    expect(task.progress).not.toHaveProperty("completed_chunks");
    expect(task.result).not.toHaveProperty("bullet_points");
  });

  it("maps paginated document list DTOs into frontend-facing models", () => {
    const responseDto: PaginatedResponseDto<DocumentTaskListItemDto> = {
      page: 1,
      page_size: 50,
      total: 1,
      items: [baseTaskListItemDto],
    };

    const response = mapPaginatedResponseDto(responseDto, mapDocumentTaskListItemDto);

    expectTypeOf(response).toEqualTypeOf<PaginatedResponse<DocumentTaskListItem>>();
    expect(response).toEqual({
      page: 1,
      pageSize: 50,
      total: 1,
      items: [
        {
          id: "task-1",
          termId: "term-1",
          status: "running",
          filename: "paper.pdf",
          currentStage: "summarize_chunks",
          progress: {
            completedChunks: 1,
            totalChunks: 3,
          },
          taskType: "summary",
          createdAt: "2026-05-06T00:00:00Z",
          updatedAt: "2026-05-06T00:00:00Z",
          retryCount: 0,
          resultPreview: "summary text",
        },
      ],
    });
    expect(response).not.toHaveProperty("page_size");
    expect(response.items[0]).not.toHaveProperty("current_stage");
  });

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
    expect(getDocumentProgressLabel(baseProgressView)).toBe("1 / 3 chunks");
  });

  it("falls back when progress data is absent or malformed", () => {
    expect(getDocumentProgressLabel(undefined)).toBe("处理中");
    expect(
      getDocumentProgressLabel({
        completedChunks: "1",
        totalChunks: 3,
      } as unknown as DocumentTaskProgressView),
    ).toBe("处理中");
  });

  it("extracts summary and bullet points safely", () => {
    expect(buildDocumentSummary(baseSummaryView)).toEqual({
      summary: "summary text",
      bulletPoints: ["point-a", "point-b"],
    });
  });

  it("returns empty summary values when result is null", () => {
    expect(buildDocumentSummary(null)).toEqual({
      summary: "",
      bulletPoints: [],
    });
  });
});
