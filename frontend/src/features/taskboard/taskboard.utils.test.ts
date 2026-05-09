import { describe, expect, it } from "vitest";

import type { Milestone } from "@/features/taskboard/taskboard.types";
import {
  buildMilestoneColumns,
  buildMilestoneSummary,
  formatDateLabel,
  getMilestoneDateRangeLabel,
  getMilestoneStatusLabel,
} from "@/features/taskboard/taskboard.utils";

const milestones: Milestone[] = [
  {
    id: "done-1",
    studentId: "student-1",
    title: "整理测试记录",
    description: null,
    startDate: "2026-05-03",
    endDate: "2026-05-04",
    status: "done",
    sortOrder: 3,
    isOverdue: false,
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: null,
  },
  {
    id: "doing-1",
    studentId: "student-1",
    title: "完成前后端联调",
    description: null,
    startDate: "2026-05-01",
    endDate: "2026-05-09",
    status: "doing",
    sortOrder: 1,
    isOverdue: true,
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: null,
  },
  {
    id: "todo-1",
    studentId: "student-1",
    title: "补充答辩材料",
    description: null,
    startDate: null,
    endDate: "2026-05-12",
    status: "todo",
    sortOrder: 2,
    isOverdue: false,
    createdAt: "2026-05-02T00:00:00Z",
    updatedAt: null,
  },
];

describe("taskboard.utils", () => {
  it("formats status and date labels", () => {
    expect(getMilestoneStatusLabel("doing")).toBe("进行中");
    expect(formatDateLabel("2026-05-09")).toBe("2026年5月9日");
    expect(getMilestoneDateRangeLabel(milestones[2]!)).toBe("截止 2026年5月12日");
  });

  it("groups milestones into status columns", () => {
    const columns = buildMilestoneColumns(milestones);

    expect(columns.map((column) => column.id)).toEqual(["todo", "doing", "done"]);
    expect(columns[0]?.items[0]?.id).toBe("todo-1");
    expect(columns[1]?.items[0]?.id).toBe("doing-1");
    expect(columns[2]?.items[0]?.id).toBe("done-1");
  });

  it("builds milestone summary counts", () => {
    expect(buildMilestoneSummary(milestones)).toEqual({
      total: 3,
      doing: 1,
      done: 1,
      overdue: 1,
    });
  });
});
