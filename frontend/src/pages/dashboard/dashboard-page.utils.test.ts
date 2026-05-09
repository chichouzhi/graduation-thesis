import { describe, expect, it } from "vitest";

import type { Conversation } from "@/features/chat/chat.types";
import type { DocumentTaskListItem } from "@/features/documents/documents.types";
import type { Milestone } from "@/features/taskboard/taskboard.types";
import type { Topic } from "@/features/topics/topics.types";
import {
  buildDashboardActivities,
  buildDashboardFocus,
  buildDashboardStatusOverview,
  buildDashboardStats,
  buildDashboardTimeline,
} from "@/pages/dashboard/dashboard-page.utils";

const snapshot = {
  conversations: [
    {
      id: "conversation-1",
      term_id: "term-1",
      title: "选题咨询",
      context_type: "topic",
      created_at: "2026-05-01T08:00:00Z",
      updated_at: "2026-05-01T09:00:00Z",
    } satisfies Conversation,
  ],
  documentTasks: [
    {
      id: "doc-1",
      termId: "term-1",
      status: "running",
      filename: "论文初稿.pdf",
      currentStage: "pdf_extract",
      progress: { completedChunks: 2, totalChunks: 8 },
      taskType: "summary",
      createdAt: "2026-05-02T08:00:00Z",
      updatedAt: "2026-05-05T10:00:00Z",
      retryCount: 0,
      resultPreview: "正在提取 PDF 内容",
    } satisfies DocumentTaskListItem,
    {
      id: "doc-2",
      termId: "term-1",
      status: "done",
      filename: "文献摘要.pdf",
      currentStage: "final_result",
      progress: { completedChunks: 8, totalChunks: 8 },
      taskType: "summary",
      createdAt: "2026-05-01T08:00:00Z",
      updatedAt: "2026-05-03T10:00:00Z",
      retryCount: 0,
      resultPreview: "摘要已生成",
    } satisfies DocumentTaskListItem,
  ],
  milestones: [
    {
      id: "mile-1",
      studentId: "student-1",
      title: "完成系统联调",
      description: "整理前后端真实接口验证记录",
      startDate: "2026-05-01",
      endDate: "2026-05-09",
      status: "doing",
      sortOrder: 1,
      isOverdue: false,
      createdAt: "2026-05-01T00:00:00Z",
      updatedAt: "2026-05-06T10:00:00Z",
    } satisfies Milestone,
    {
      id: "mile-2",
      studentId: "student-1",
      title: "补充论文草稿",
      description: null,
      startDate: "2026-05-01",
      endDate: "2026-05-10",
      status: "done",
      sortOrder: 2,
      isOverdue: false,
      createdAt: "2026-05-01T00:00:00Z",
      updatedAt: "2026-05-04T10:00:00Z",
    } satisfies Milestone,
  ],
  topics: [
    {
      id: "topic-1",
      title: "AI 学术助手工作台",
      summary: "面向毕业设计的 AI 工作台",
      requirements: "熟悉 React、Flask 和异步任务",
      techKeywords: ["AI 助手", "异步任务"],
      capacity: 2,
      selectedCount: 1,
      teacherId: "teacher-1",
      termId: "term-1",
      status: "published",
      portrait: {
        keywords: ["画像", "推荐"],
        difficultyLabel: "advanced",
        difficultyReason: "跨前端、后端与异步任务",
        requiredCapabilities: ["React", "Flask"],
        suitableStudents: ["有项目经验的学生"],
        risks: ["范围较大"],
        summary: "这是一个适合答辩展示的综合题目。",
        extractedAt: "2026-05-04T00:00:00Z",
      },
      llmKeywordJobId: "job-1",
      llmKeywordJobStatus: "done",
      createdAt: "2026-05-01T00:00:00Z",
      updatedAt: "2026-05-06T12:00:00Z",
    } satisfies Topic,
    {
      id: "topic-2",
      title: "选题推荐分析",
      summary: "帮助学生进行选题推荐",
      requirements: "理解推荐逻辑",
      techKeywords: ["推荐", "画像"],
      capacity: 2,
      selectedCount: 0,
      teacherId: "teacher-1",
      termId: "term-1",
      status: "draft",
      portrait: null,
      llmKeywordJobId: "job-2",
      llmKeywordJobStatus: "running",
      createdAt: "2026-05-02T00:00:00Z",
      updatedAt: "2026-05-05T12:00:00Z",
    } satisfies Topic,
  ],
};

describe("dashboard-page.utils", () => {
  it("builds aggregated dashboard stats and status overview", () => {
    expect(buildDashboardStats(snapshot)).toEqual([
      {
        id: "topics",
        label: "题目画像",
        value: "2",
        hint: "1 个题目已完成分析",
      },
      {
        id: "documents",
        label: "文档任务",
        value: "2",
        hint: "1 个文档仍在处理中",
      },
      {
        id: "running",
        label: "进行中",
        value: "3",
        hint: "跨题目、文档与里程碑统计",
      },
      {
        id: "completed",
        label: "已完成",
        value: "3",
        hint: "当前学期的终态节点",
      },
    ]);

    expect(buildDashboardStatusOverview(snapshot).map((item) => item.status)).toEqual([
      "running",
      "running",
      "running",
    ]);
    expect(buildDashboardFocus(snapshot)).toContain("正在推进");
  });

  it("builds recent timeline and activity cards in descending order", () => {
    expect(buildDashboardTimeline(snapshot).map((item) => item.id)).toEqual([
      "topic-topic-1",
      "milestone-mile-1",
      "document-doc-1",
    ]);

    expect(buildDashboardActivities(snapshot).map((item) => item.id)).toEqual([
      "topic-topic-1",
      "milestone-mile-1",
      "document-doc-1",
    ]);
  });
});
