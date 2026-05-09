import { describe, expect, it } from "vitest";

import {
  mapMilestoneDto,
  mapPaginatedResponseDto,
  type MilestoneDto,
} from "@/features/taskboard/taskboard.types";

describe("taskboard.types", () => {
  it("maps milestone dto into frontend model", () => {
    const milestone: MilestoneDto = {
      id: "milestone-1",
      student_id: "student-1",
      title: "完成系统联调",
      description: "整理前后端真实接口验证记录",
      start_date: "2026-05-01",
      end_date: "2026-05-09",
      status: "doing",
      sort_order: 2,
      is_overdue: true,
      created_at: "2026-05-01T00:00:00Z",
      updated_at: "2026-05-08T00:00:00Z",
    };

    expect(mapMilestoneDto(milestone)).toEqual({
      id: "milestone-1",
      studentId: "student-1",
      title: "完成系统联调",
      description: "整理前后端真实接口验证记录",
      startDate: "2026-05-01",
      endDate: "2026-05-09",
      status: "doing",
      sortOrder: 2,
      isOverdue: true,
      createdAt: "2026-05-01T00:00:00Z",
      updatedAt: "2026-05-08T00:00:00Z",
    });
  });

  it("maps paginated milestone list metadata", () => {
    const response = mapPaginatedResponseDto(
      {
        page: 1,
        page_size: 50,
        total: 1,
        items: [
          {
            id: "milestone-1",
            student_id: "student-1",
            title: "完成系统联调",
            status: "todo",
            created_at: "2026-05-01T00:00:00Z",
          } satisfies MilestoneDto,
        ],
      },
      mapMilestoneDto,
    );

    expect(response.pageSize).toBe(50);
    expect(response.total).toBe(1);
    expect(response.items[0]?.sortOrder).toBe(0);
    expect(response.items[0]?.isOverdue).toBe(false);
  });
});
