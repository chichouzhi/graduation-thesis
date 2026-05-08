import type { ActivityItem, AsyncStatus } from "@/types/app";

export const dashboardStats = [
  { id: "conversations", label: "会话总数", value: "12", hint: "近 7 天新增 4 个" },
  { id: "documents", label: "文档任务", value: "8", hint: "其中 2 个仍在处理中" },
  { id: "running", label: "进行中任务", value: "3", hint: "聊天与文档任务混合统计" },
  { id: "completed", label: "本周完成", value: "6", hint: "较上周多 2 个" },
];

export const dashboardTimeline: Array<{
  id: string;
  title: string;
  detail: string;
  status: AsyncStatus;
}> = [
  { id: "w1", title: "比较选题推荐算法", detail: "梳理标签匹配与语义关键词方案", status: "running" },
  { id: "w2", title: "复核文献摘要结果", detail: "确认两篇教育 AI 论文的研究结论", status: "pending" },
  { id: "w3", title: "更新阶段任务进度", detail: "将接口联调与论文设计章节同步推进", status: "done" },
];

export const dashboardActivities: ActivityItem[] = [
  { id: "a1", title: "AI 助手完成选题匹配建议", description: "已基于兴趣标签生成 3 个候选课题的比较说明。", time: "10 分钟前" },
  { id: "a2", title: "PDF 文献解析进入运行中", description: "《RAG for Education.pdf》正在抽取研究方法与关键结论。", time: "35 分钟前" },
  { id: "a3", title: "任务看板更新实现节点", description: "新增“推荐规则校验”和“志愿状态联调”两项任务。", time: "今天 09:20" },
];

export const dashboardStatusOverview = [
  {
    id: "s1",
    label: "聊天任务",
    status: "running" as AsyncStatus,
    detail: "当前有 1 条 assistant 回复仍在生成中。",
  },
  {
    id: "s2",
    label: "文档处理",
    status: "pending" as AsyncStatus,
    detail: "新上传 PDF 已受理，等待进入分块总结阶段。",
  },
  {
    id: "s3",
    label: "最近终态",
    status: "failed" as AsyncStatus,
    detail: "有 1 个历史文档任务因解析失败需要重新上传。",
  },
];
