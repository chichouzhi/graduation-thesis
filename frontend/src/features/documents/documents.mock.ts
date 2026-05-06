import type { AsyncStatus } from "@/types/app";

export const documentTasks: Array<{
  id: string;
  filename: string;
  status: AsyncStatus;
  currentStage: string;
  progress: string;
}> = [
  { id: "doc-1", filename: "RAG-for-Education.pdf", status: "running", currentStage: "chunk_summarizing", progress: "8 / 12 页块" },
  { id: "doc-2", filename: "Thesis-Outline.pdf", status: "done", currentStage: "final_result", progress: "已完成" },
  { id: "doc-3", filename: "Survey-Paper.pdf", status: "failed", currentStage: "pdf_extract", progress: "解析失败" },
];

export const documentDetail: {
  id: string;
  filename: string;
  status: AsyncStatus;
  taskType: string;
  language: string;
  stages: Array<{ label: string; value: AsyncStatus }>;
  summary: string;
  bulletPoints: string[];
} = {
  id: "doc-1",
  filename: "RAG-for-Education.pdf",
  status: "running",
  taskType: "summary",
  language: "zh",
  stages: [
    { label: "上传受理", value: "done" },
    { label: "PDF 解析", value: "done" },
    { label: "分块总结", value: "running" },
    { label: "聚合结果", value: "pending" },
  ],
  summary:
    "该论文聚焦检索增强生成在教育场景中的应用价值，强调知识可信度、来源可追溯和回答结构化呈现。",
  bulletPoints: [
    "提出面向学习者问答的 RAG 流程设计。",
    "关注引用透明度与知识更新问题。",
    "适合映射到本项目的学术助手场景。",
  ],
};

export const documentFailureNote = {
  title: "失败态预留",
  description:
    "当任务进入 failed 时，这里会展示 error_code、error_message 和建议操作。本轮先用静态提示明确预留这块区域。",
  latestFailedTask: "Survey-Paper.pdf",
};
