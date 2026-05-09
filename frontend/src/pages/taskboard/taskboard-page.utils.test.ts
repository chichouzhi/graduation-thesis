import { describe, expect, it } from "vitest";

import {
  buildCreateMilestoneRequest,
  buildPatchMilestoneStatusRequest,
  type MilestoneDraft,
} from "@/pages/taskboard/taskboard-page.utils";

describe("taskboard-page.utils", () => {
  it("builds create milestone request from form draft", () => {
    const draft: MilestoneDraft = {
      title: " 完成前后端联调 ",
      description: " 整理接口验证记录 ",
      startDate: "2026-05-01",
      endDate: "2026-05-09",
      status: "doing",
      sortOrder: "2",
    };

    expect(buildCreateMilestoneRequest(draft)).toEqual({
      title: "完成前后端联调",
      description: "整理接口验证记录",
      start_date: "2026-05-01",
      end_date: "2026-05-09",
      status: "doing",
      sort_order: 2,
    });
  });

  it("normalizes optional fields and invalid sort order", () => {
    const draft: MilestoneDraft = {
      title: "补充答辩材料",
      description: " ",
      startDate: "",
      endDate: "2026-05-12",
      status: "todo",
      sortOrder: "abc",
    };

    expect(buildCreateMilestoneRequest(draft)).toEqual({
      title: "补充答辩材料",
      description: null,
      start_date: "",
      end_date: "2026-05-12",
      status: "todo",
      sort_order: 0,
    });
  });

  it("builds minimal status patch request", () => {
    expect(buildPatchMilestoneStatusRequest("done")).toEqual({
      status: "done",
    });
  });
});
