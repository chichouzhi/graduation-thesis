import { describe, expect, it } from "vitest";

import {
  mapRecommendationTopicListDto,
  mapTopicDto,
  type RecommendationTopicListDto,
  type TopicDto,
} from "@/features/topics/topics.types";
import {
  buildTopicCapacityLabel,
  getTopicKeywordGroups,
  getTopicStatusLabel,
} from "@/features/topics/topics.utils";

const topicDto: TopicDto = {
  id: "topic-1",
  title: "面向毕业设计场景的 AI 学术助手工作台设计与实现",
  summary: "围绕异步聊天、PDF 文档处理与任务协同构建学生端产品。",
  requirements: "熟悉 React、Flask、异步任务队列与学术场景分析。",
  tech_keywords: ["AI 助手", "异步任务"],
  capacity: 2,
  selected_count: 1,
  teacher_id: "teacher-1",
  term_id: "term-2026-spring",
  status: "published",
  portrait: {
    keywords: ["工作台", "文档理解"],
    difficulty_label: "advanced",
    difficulty_reason: "需要同时覆盖前端、后端和异步任务。",
    required_capabilities: ["React", "Flask", "任务编排"],
    suitable_students: ["有完整项目经验的学生"],
    risks: ["范围较大，需要严格拆分阶段"],
    summary: "这是一个跨前后端与 AI 工作流整合的题目。",
    extracted_at: "2026-05-06T00:00:00Z",
  },
  llm_keyword_job_id: "job-1",
  llm_keyword_job_status: "done",
  created_at: "2026-05-06T00:00:00Z",
  updated_at: "2026-05-06T00:00:00Z",
};

const recommendationDto: RecommendationTopicListDto = {
  top_n: 10,
  items: [
    {
      topic_id: "topic-1",
      title: "面向毕业设计场景的 AI 学术助手工作台设计与实现",
      score: 92,
      explain: {
        matched_skills: ["React"],
        matched_keywords: ["异步任务"],
        matched_capabilities: ["前端实现", "任务编排"],
        difficulty_fit: "学生每周投入时间可覆盖进阶难度要求",
        capacity_status: "available",
        warnings: ["仍需补足推荐解释模块"],
        reasons: ["题目画像与学生画像高度重合"],
      },
    },
  ],
};

describe("topics.utils", () => {
  it("maps topic dto into frontend model", () => {
    const topic = mapTopicDto(topicDto);

    expect(topic.techKeywords).toEqual(["AI 助手", "异步任务"]);
    expect(topic.selectedCount).toBe(1);
    expect(topic.portrait).toEqual({
      keywords: ["工作台", "文档理解"],
      difficultyLabel: "advanced",
      difficultyReason: "需要同时覆盖前端、后端和异步任务。",
      requiredCapabilities: ["React", "Flask", "任务编排"],
      suitableStudents: ["有完整项目经验的学生"],
      risks: ["范围较大，需要严格拆分阶段"],
      summary: "这是一个跨前后端与 AI 工作流整合的题目。",
      extractedAt: "2026-05-06T00:00:00Z",
    });
    expect(topic.llmKeywordJobStatus).toBe("done");
  });

  it("maps recommendation dto into frontend model", () => {
    const recommendations = mapRecommendationTopicListDto(recommendationDto);

    expect(recommendations.topN).toBe(10);
    expect(recommendations.items[0]?.topicId).toBe("topic-1");
    expect(recommendations.items[0]?.explain).toEqual({
      matchedSkills: ["React"],
      matchedKeywords: ["异步任务"],
      matchedCapabilities: ["前端实现", "任务编排"],
      difficultyFit: "学生每周投入时间可覆盖进阶难度要求",
      capacityStatus: "available",
      warnings: ["仍需补足推荐解释模块"],
      reasons: ["题目画像与学生画像高度重合"],
    });
  });

  it("formats topic status labels", () => {
    expect(getTopicStatusLabel("published")).toBe("可选题");
    expect(getTopicStatusLabel("pending_review")).toBe("待审核");
  });

  it("formats capacity labels", () => {
    const topic = mapTopicDto(topicDto);

    expect(buildTopicCapacityLabel(topic)).toBe("1 / 2 人");
  });

  it("prefers portrait keywords when available", () => {
    const topic = mapTopicDto(topicDto);

    expect(getTopicKeywordGroups(topic)).toEqual({
      primary: ["AI 助手", "异步任务"],
      derived: ["工作台", "文档理解"],
    });
  });
});
