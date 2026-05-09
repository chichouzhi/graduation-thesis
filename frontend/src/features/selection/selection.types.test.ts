import { describe, expect, it } from "vitest";

import {
  buildCreateApplicationRequest,
  mapApplicationDto,
  mapPaginatedResponseDto,
  type ApplicationDto,
} from "@/features/selection/selection.types";

describe("selection.types", () => {
  it("maps application dto into frontend model", () => {
    const application: ApplicationDto = {
      id: "application-1",
      topic_id: "topic-1",
      topic_title: "AI 学术助手工作台",
      student_id: "student-1",
      term_id: "term-2026-spring",
      priority: 1,
      status: "pending",
      created_at: "2026-05-09T00:00:00Z",
      updated_at: "2026-05-09T01:00:00Z",
    };

    expect(mapApplicationDto(application)).toEqual({
      id: "application-1",
      topicId: "topic-1",
      topicTitle: "AI 学术助手工作台",
      studentId: "student-1",
      termId: "term-2026-spring",
      priority: 1,
      status: "pending",
      createdAt: "2026-05-09T00:00:00Z",
      updatedAt: "2026-05-09T01:00:00Z",
    });
  });

  it("builds create application request from selected topic", () => {
    expect(buildCreateApplicationRequest("topic-1", "term-2026-spring", 2)).toEqual({
      topic_id: "topic-1",
      term_id: "term-2026-spring",
      priority: 2,
    });
  });

  it("maps paginated application response metadata", () => {
    const response = mapPaginatedResponseDto(
      {
        page: 1,
        page_size: 20,
        total: 1,
        items: [
          {
            id: "application-1",
            topic_id: "topic-1",
            topic_title: "AI 学术助手工作台",
            student_id: "student-1",
            term_id: "term-2026-spring",
            priority: 1,
            status: "accepted",
            created_at: "2026-05-09T00:00:00Z",
          } satisfies ApplicationDto,
        ],
      },
      mapApplicationDto,
    );

    expect(response.pageSize).toBe(20);
    expect(response.items[0]?.status).toBe("accepted");
    expect(response.items[0]?.updatedAt).toBeNull();
  });
});
