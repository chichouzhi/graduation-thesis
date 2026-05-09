import { describe, expect, it } from "vitest";

import {
  buildCreateTopicRequest,
  buildPatchTopicRequest,
  buildStudentProfilePatch,
  mapStudentProfileToDraft,
  parseDraftTerms,
} from "@/pages/topics/topics-page.utils";

describe("topics-page.utils", () => {
  it("parses comma-like terms into unique values", () => {
    expect(parseDraftTerms("React，Flask, React\n异步任务")).toEqual([
      "React",
      "Flask",
      "异步任务",
    ]);
  });

  it("builds create topic payload from teacher draft", () => {
    expect(
      buildCreateTopicRequest(
        {
          title: "AI 学术助手工作台",
          summary: "面向毕业设计的工作台",
          requirements: "熟悉 React、Flask 和异步任务",
          keywords: "AI 助手，异步任务，工作台",
          capacity: "2",
        },
        "term-2026-spring",
      ),
    ).toEqual({
      title: "AI 学术助手工作台",
      summary: "面向毕业设计的工作台",
      requirements: "熟悉 React、Flask 和异步任务",
      tech_keywords: ["AI 助手", "异步任务", "工作台"],
      capacity: 2,
      term_id: "term-2026-spring",
    });
  });

  it("builds patch topic payload from teacher draft", () => {
    expect(
      buildPatchTopicRequest({
        title: "AI 学术助手工作台",
        summary: "面向毕业设计的工作台",
        requirements: "熟悉 React、Flask 和异步任务",
        keywords: "AI 助手，异步任务，工作台",
        capacity: "2",
      }),
    ).toEqual({
      title: "AI 学术助手工作台",
      summary: "面向毕业设计的工作台",
      requirements: "熟悉 React、Flask 和异步任务",
      tech_keywords: ["AI 助手", "异步任务", "工作台"],
      capacity: 2,
    });
  });

  it("hydrates student draft from saved profile", () => {
    expect(
      mapStudentProfileToDraft({
        interests: ["AI 学术助手", "选题推荐"],
        skills: ["React", "Flask"],
        keywords: ["画像"],
        goal: "做一个适合答辩展示的系统",
        weeklyHours: 8,
      }),
    ).toEqual({
      interests: "AI 学术助手，选题推荐",
      skills: "React，Flask",
      keywords: "画像",
      goal: "做一个适合答辩展示的系统",
      weeklyHours: "8",
    });
  });

  it("builds patch user me payload from student draft", () => {
    expect(
      buildStudentProfilePatch({
        interests: "AI 学术助手，选题推荐",
        skills: "React，Flask",
        keywords: "画像，可解释推荐",
        goal: "做一个适合答辩展示的系统",
        weeklyHours: "10",
      }),
    ).toEqual({
      student_profile: {
        interests: ["AI 学术助手", "选题推荐"],
        skills: ["React", "Flask"],
        keywords: ["画像", "可解释推荐"],
        goal: "做一个适合答辩展示的系统",
        weekly_hours: 10,
      },
    });
  });
});
