import type { AsyncStatus } from "@/types/app";

export const conversations = [
  { id: "conv-1", title: "RAG 在学术问答中的应用", updatedAt: "刚刚" },
  { id: "conv-2", title: "毕业设计任务拆解建议", updatedAt: "今天 11:10" },
  { id: "conv-3", title: "开题报告研究现状整理", updatedAt: "昨天" },
];

export const messages: Array<{
  id: string;
  role: "user" | "assistant";
  content: string;
  status: AsyncStatus | null;
}> = [
  { id: "m-1", role: "user", content: "请帮我比较一下选题推荐和文档摘要两个模块的实现重点。", status: null },
  { id: "m-2", role: "assistant", content: "选题推荐更关注课题画像、学生偏好和可解释匹配；文档摘要更关注 PDF 解析、分块处理和结果回写。", status: "done" },
  { id: "m-3", role: "assistant", content: "正在补充志愿状态与任务链路说明…", status: "running" },
  { id: "m-4", role: "assistant", content: "一个历史任务因为超时而失败，可在页面中清楚展示。", status: "failed" },
  { id: "m-5", role: "assistant", content: "", status: "pending" },
];
