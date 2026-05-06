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
  DocumentTaskProgress,
} from "@/features/documents/documents.types";

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
  it("uses explicit DTO aliases for current API-shaped task types", () => {
    expectTypeOf<DocumentTask>().toEqualTypeOf<DocumentTaskDto>();
    expectTypeOf<DocumentTask["progress"]>().toEqualTypeOf<
      DocumentTaskProgress | undefined
    >();
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
    expect(getDocumentProgressLabel(baseTask)).toBe("1 / 3 chunks");
  });

  it("falls back when progress data is absent or malformed", () => {
    expect(getDocumentProgressLabel({ progress: undefined })).toBe("处理中");
    expect(
      getDocumentProgressLabel({
        progress: {
          completed_chunks: "1",
          total_chunks: 3,
        } as unknown as DocumentTaskProgress,
      }),
    ).toBe("处理中");
  });

  it("extracts summary and bullet points safely", () => {
    expect(buildDocumentSummary(baseTask)).toEqual({
      summary: "summary text",
      bulletPoints: ["point-a", "point-b"],
    });
  });

  it("returns empty summary values when result is null", () => {
    expect(buildDocumentSummary({ result: null })).toEqual({
      summary: "",
      bulletPoints: [],
    });
  });
});
