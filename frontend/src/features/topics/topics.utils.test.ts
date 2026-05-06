import { describe, expect, it } from "vitest";

import {
  mapTopicDto,
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
    extracted_at: "2026-05-06T00:00:00Z",
  },
  llm_keyword_job_id: "job-1",
  llm_keyword_job_status: "done",
  created_at: "2026-05-06T00:00:00Z",
  updated_at: "2026-05-06T00:00:00Z",
};

describe("topics.utils", () => {
  it("maps topic dto into frontend model", () => {
    const topic = mapTopicDto(topicDto);

    expect(topic.techKeywords).toEqual(["AI 助手", "异步任务"]);
    expect(topic.selectedCount).toBe(1);
    expect(topic.portrait?.keywords).toEqual(["工作台", "文档理解"]);
    expect(topic.llmKeywordJobStatus).toBe("done");
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
