import { describe, expect, it } from "vitest";

import { mapUserMeDto, type UserMeDto } from "@/features/users/users.types";

describe("users.types", () => {
  it("maps user me dto and student profile into frontend model", () => {
    const user: UserMeDto = {
      id: "user-1",
      username: "student-demo",
      role: "student",
      display_name: "联调学生",
      email: "student@example.com",
      student_profile: {
        interests: ["AI 学术助手", "选题推荐"],
        skills: ["React", "Flask"],
        keywords: ["画像", "异步任务"],
        goal: "希望完成可用于答辩演示的毕业设计",
        weekly_hours: 10,
      },
      teacher_profile: null,
    };

    expect(mapUserMeDto(user)).toEqual({
      id: "user-1",
      username: "student-demo",
      role: "student",
      displayName: "联调学生",
      email: "student@example.com",
      studentProfile: {
        interests: ["AI 学术助手", "选题推荐"],
        skills: ["React", "Flask"],
        keywords: ["画像", "异步任务"],
        goal: "希望完成可用于答辩演示的毕业设计",
        weeklyHours: 10,
      },
      teacherProfile: null,
    });
  });
});
