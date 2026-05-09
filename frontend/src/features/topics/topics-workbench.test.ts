import { describe, expect, it } from "vitest";

import type { Topic } from "@/features/topics/topics.types";
import {
  buildTopicAnalysis,
  buildTopicRecommendations,
  parseWorkbenchTerms,
} from "@/features/topics/topics-workbench";

const publishedTopic: Topic = {
  id: "topic-1",
  title: "面向毕业设计场景的 AI 选题推荐工作台",
  summary: "围绕题目画像、学生画像和推荐解释实现可演示工作台。",
  requirements: "熟悉 React、Flask、推荐逻辑与异步任务状态管理。",
  techKeywords: ["AI 助手", "选题推荐", "React"],
  capacity: 2,
  selectedCount: 1,
  teacherId: "teacher-1",
  termId: "term-2026-spring",
  status: "published",
  portrait: {
    keywords: ["画像", "异步任务", "可解释推荐"],
    extractedAt: "2026-05-08T00:00:00Z",
  },
  llmKeywordJobId: "job-1",
  llmKeywordJobStatus: "done",
  createdAt: "2026-05-08T00:00:00Z",
  updatedAt: "2026-05-08T00:00:00Z",
};

const secondaryTopic: Topic = {
  id: "topic-2",
  title: "毕业论文文献分析助手",
  summary: "聚焦 PDF 摘要生成与文档对比分析。",
  requirements: "熟悉文档解析、摘要生成和结果展示。",
  techKeywords: ["PDF", "文档摘要"],
  capacity: 1,
  selectedCount: 1,
  teacherId: "teacher-2",
  termId: "term-2026-spring",
  status: "published",
  portrait: {
    keywords: ["对比分析"],
    extractedAt: "2026-05-08T00:00:00Z",
  },
  llmKeywordJobId: "job-2",
  llmKeywordJobStatus: "done",
  createdAt: "2026-05-08T00:00:00Z",
  updatedAt: "2026-05-08T00:00:00Z",
};

describe("topics-workbench", () => {
  it("parses comma-like term inputs into unique values", () => {
    expect(parseWorkbenchTerms("React，Flask, React\n异步任务")).toEqual([
      "React",
      "Flask",
      "异步任务",
    ]);
  });

  it("builds teacher-side topic analysis summary", () => {
    const analysis = buildTopicAnalysis({
      title: publishedTopic.title,
      summary: publishedTopic.summary,
      requirements: publishedTopic.requirements,
      keywords: "AI 助手，选题推荐，异步任务",
      capacity: "2",
    });

    expect(analysis.focusKeywords).toContain("AI 助手");
    expect(analysis.requiredCapabilities).toContain("模型调用与语义分析");
    expect(analysis.summary).toContain("系统会把题目拆成关键词");
  });

  it("ranks published topics against student input", () => {
    const recommendations = buildTopicRecommendations(
      [secondaryTopic, publishedTopic],
      {
        interests: "AI 助手，选题推荐",
        skills: "React，异步任务",
        keywords: "画像，可解释推荐",
        goal: "希望完成一个可答辩展示的推荐系统",
        weeklyHours: "10",
      },
    );

    expect(recommendations[0]?.topic.id).toBe("topic-1");
    expect(recommendations[0]?.matchedTerms).toContain("React");
    expect(recommendations[1]?.warning).toBe("该题目容量已满");
  });
});
