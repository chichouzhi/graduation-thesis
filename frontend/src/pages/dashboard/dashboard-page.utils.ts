import type { Conversation } from "@/features/chat/chat.types";
import type { DocumentTaskListItem } from "@/features/documents/documents.types";
import type { Milestone } from "@/features/taskboard/taskboard.types";
import type { Topic } from "@/features/topics/topics.types";
import type { ActivityItem, AsyncStatus } from "@/types/app";

export type DashboardSnapshot = {
  conversations: Conversation[];
  documentTasks: DocumentTaskListItem[];
  milestones: Milestone[];
  topics: Topic[];
};

export type DashboardStat = {
  id: string;
  label: string;
  value: string;
  hint: string;
};

export type DashboardStatusOverviewItem = {
  id: string;
  label: string;
  status: AsyncStatus;
  detail: string;
};

export type DashboardTimelineItem = {
  id: string;
  title: string;
  detail: string;
  status: AsyncStatus;
};

function toTimestamp(value?: string | null) {
  if (!value) {
    return 0;
  }

  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDateTimeLabel(value?: string | null) {
  if (!value) {
    return "刚刚";
  }

  if (!value.includes("T")) {
    return value;
  }

  return value.replace("T", " ").replace("Z", "");
}

function getRunningTopicCount(topics: Topic[]) {
  return topics.filter((topic) => topic.llmKeywordJobStatus === "pending" || topic.llmKeywordJobStatus === "running").length;
}

function getDoneTopicCount(topics: Topic[]) {
  return topics.filter((topic) => topic.llmKeywordJobStatus === "done").length;
}

function getFailedTopicCount(topics: Topic[]) {
  return topics.filter((topic) => topic.llmKeywordJobStatus === "failed").length;
}

function getDocumentStatusCounts(documentTasks: DocumentTaskListItem[]) {
  return {
    pending: documentTasks.filter((task) => task.status === "pending").length,
    running: documentTasks.filter((task) => task.status === "running").length,
    done: documentTasks.filter((task) => task.status === "done").length,
    failed: documentTasks.filter((task) => task.status === "failed").length,
  };
}

function getMilestoneStatusCounts(milestones: Milestone[]) {
  return {
    todo: milestones.filter((milestone) => milestone.status === "todo").length,
    doing: milestones.filter((milestone) => milestone.status === "doing").length,
    done: milestones.filter((milestone) => milestone.status === "done").length,
    overdue: milestones.filter((milestone) => milestone.isOverdue).length,
  };
}

function getTimelineStatus(status: "todo" | "doing" | "done" | "pending" | "running" | "failed"): AsyncStatus {
  switch (status) {
    case "todo":
    case "pending":
      return "pending";
    case "doing":
    case "running":
      return "running";
    case "done":
      return "done";
    case "failed":
      return "failed";
  }
}

export function buildDashboardStats(snapshot: DashboardSnapshot): DashboardStat[] {
  const topicPortraitCount = getDoneTopicCount(snapshot.topics);
  const documentCounts = getDocumentStatusCounts(snapshot.documentTasks);
  const milestoneCounts = getMilestoneStatusCounts(snapshot.milestones);
  const activeCount =
    getRunningTopicCount(snapshot.topics) +
    documentCounts.pending +
    documentCounts.running +
    milestoneCounts.doing +
    milestoneCounts.todo;
  const doneCount = topicPortraitCount + documentCounts.done + milestoneCounts.done;

  return [
    {
      id: "topics",
      label: "题目画像",
      value: String(snapshot.topics.length),
      hint: `${topicPortraitCount} 个题目已完成分析`,
    },
    {
      id: "documents",
      label: "文档任务",
      value: String(snapshot.documentTasks.length),
      hint: `${documentCounts.pending + documentCounts.running} 个文档仍在处理中`,
    },
    {
      id: "running",
      label: "进行中",
      value: String(activeCount),
      hint: "跨题目、文档与里程碑统计",
    },
    {
      id: "completed",
      label: "已完成",
      value: String(doneCount),
      hint: "当前学期的终态节点",
    },
  ];
}

export function buildDashboardStatusOverview(snapshot: DashboardSnapshot): DashboardStatusOverviewItem[] {
  const topicDone = getDoneTopicCount(snapshot.topics);
  const topicRunning = getRunningTopicCount(snapshot.topics);
  const topicFailed = getFailedTopicCount(snapshot.topics);

  const documentCounts = getDocumentStatusCounts(snapshot.documentTasks);
  const milestoneCounts = getMilestoneStatusCounts(snapshot.milestones);

  const topicStatus: AsyncStatus =
    topicFailed > 0 ? "failed" : topicRunning > 0 ? "running" : topicDone > 0 ? "done" : "pending";
  const documentStatus: AsyncStatus =
    documentCounts.failed > 0
      ? "failed"
      : documentCounts.pending + documentCounts.running > 0
        ? "running"
        : documentCounts.done > 0
          ? "done"
          : "pending";
  const milestoneStatus: AsyncStatus =
    milestoneCounts.overdue > 0 ? "failed" : milestoneCounts.doing > 0 || milestoneCounts.todo > 0 ? "running" : "done";

  return [
    {
      id: "topics",
      label: "题目画像",
      status: topicStatus,
      detail: `${topicDone} 个已完成，${topicRunning} 个分析中。`,
    },
    {
      id: "documents",
      label: "文档处理",
      status: documentStatus,
      detail: `${documentCounts.running} 个处理中，${documentCounts.done} 个已完成。`,
    },
    {
      id: "milestones",
      label: "阶段任务",
      status: milestoneStatus,
      detail: `${milestoneCounts.doing} 个进行中，${milestoneCounts.overdue} 个逾期。`,
    },
  ];
}

export function buildDashboardTimeline(snapshot: DashboardSnapshot): DashboardTimelineItem[] {
  const topicTimeline = snapshot.topics
    .slice()
    .sort((left, right) => toTimestamp(right.updatedAt) - toTimestamp(left.updatedAt))
    .slice(0, 1)
    .map((topic) => ({
      id: `topic-${topic.id}`,
      title: `题目画像：${topic.title}`,
      detail: topic.portrait?.summary ?? topic.summary,
      status: getTimelineStatus(topic.llmKeywordJobStatus ?? "pending"),
      timestamp: toTimestamp(topic.updatedAt),
    }));

  const documentTimeline = snapshot.documentTasks
    .slice()
    .sort((left, right) => toTimestamp(right.updatedAt) - toTimestamp(left.updatedAt))
    .slice(0, 1)
    .map((task) => ({
      id: `document-${task.id}`,
      title: `文档任务：${task.filename}`,
      detail: task.resultPreview ?? task.currentStage ?? "文档处理中",
      status: getTimelineStatus(task.status),
      timestamp: toTimestamp(task.updatedAt),
    }));

  const milestoneTimeline = snapshot.milestones
    .slice()
    .sort((left, right) => toTimestamp(right.updatedAt) - toTimestamp(left.updatedAt))
    .slice(0, 1)
    .map((milestone) => ({
      id: `milestone-${milestone.id}`,
      title: `里程碑：${milestone.title}`,
      detail: `${milestone.isOverdue ? "已逾期" : "截止"} ${milestone.endDate ?? milestone.createdAt.slice(0, 10)}`,
      status: getTimelineStatus(milestone.status),
      timestamp: toTimestamp(milestone.updatedAt),
    }));

  return [...topicTimeline, ...documentTimeline, ...milestoneTimeline]
    .sort((left, right) => right.timestamp - left.timestamp)
    .map((item) => ({
      id: item.id,
      title: item.title,
      detail: item.detail,
      status: item.status,
    }));
}

export function buildDashboardActivities(snapshot: DashboardSnapshot): ActivityItem[] {
  const items: Array<ActivityItem & { timestamp: number }> = [];

  const latestConversation = snapshot.conversations
    .slice()
    .sort((left, right) => toTimestamp(right.updated_at) - toTimestamp(left.updated_at))[0];
  if (latestConversation) {
    items.push({
      id: `conversation-${latestConversation.id}`,
      title: `会话更新：${latestConversation.title ?? "未命名会话"}`,
      description: `上下文：${latestConversation.context_type ?? "general"}，最近更新时间 ${formatDateTimeLabel(latestConversation.updated_at ?? latestConversation.created_at)}`,
      time: formatDateTimeLabel(latestConversation.updated_at ?? latestConversation.created_at),
      timestamp: toTimestamp(latestConversation.updated_at ?? latestConversation.created_at),
    });
  }

  const latestTopic = snapshot.topics
    .slice()
    .sort((left, right) => toTimestamp(right.updatedAt) - toTimestamp(left.updatedAt))[0];
  if (latestTopic) {
    items.push({
      id: `topic-${latestTopic.id}`,
      title: `题目画像同步：${latestTopic.title}`,
      description: latestTopic.portrait?.keywords.length
        ? `已抽取 ${latestTopic.portrait.keywords.length} 个关键词，分析状态 ${latestTopic.llmKeywordJobStatus ?? "pending"}。`
        : `当前状态 ${latestTopic.llmKeywordJobStatus ?? "pending"}。`,
      time: formatDateTimeLabel(latestTopic.updatedAt),
      timestamp: toTimestamp(latestTopic.updatedAt),
    });
  }

  const latestDocument = snapshot.documentTasks
    .slice()
    .sort((left, right) => toTimestamp(right.updatedAt) - toTimestamp(left.updatedAt))[0];
  if (latestDocument) {
    items.push({
      id: `document-${latestDocument.id}`,
      title: `PDF 任务更新：${latestDocument.filename}`,
      description: `当前阶段：${latestDocument.currentStage ?? "处理中"}，状态 ${latestDocument.status}。`,
      time: formatDateTimeLabel(latestDocument.updatedAt),
      timestamp: toTimestamp(latestDocument.updatedAt),
    });
  }

  const latestMilestone = snapshot.milestones
    .slice()
    .sort((left, right) => toTimestamp(right.updatedAt) - toTimestamp(left.updatedAt))[0];
  if (latestMilestone) {
    items.push({
      id: `milestone-${latestMilestone.id}`,
      title: `里程碑更新：${latestMilestone.title}`,
      description: `阶段状态 ${latestMilestone.status}，${latestMilestone.isOverdue ? "已逾期" : `截止 ${latestMilestone.endDate ?? "未设置"}`}`,
      time: formatDateTimeLabel(latestMilestone.updatedAt),
      timestamp: toTimestamp(latestMilestone.updatedAt),
    });
  }

  return items
    .sort((left, right) => right.timestamp - left.timestamp)
    .slice(0, 3)
    .map((item) => ({
      id: item.id,
      title: item.title,
      description: item.description,
      time: item.time,
    }));
}

export function buildDashboardFocus(snapshot: DashboardSnapshot) {
  const statusOverview = buildDashboardStatusOverview(snapshot);
  const hasRunning = statusOverview.some((item) => item.status === "running");
  const hasFailed = statusOverview.some((item) => item.status === "failed");

  if (hasFailed) {
    return "当前有逾期或失败节点，建议优先处理任务看板和异步任务。";
  }

  if (hasRunning) {
    return "题目分析、文档处理和阶段任务正在推进，适合继续跟进最新结果。";
  }

  return "工作台已准备就绪，可以继续发起新的聊天、文档和选题任务。";
}
