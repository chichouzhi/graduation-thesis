import type { Topic, TopicStatus } from "@/features/topics/topics.types";

const topicStatusLabels: Record<TopicStatus, string> = {
  draft: "草稿",
  pending_review: "待审核",
  published: "可选题",
  rejected: "已驳回",
  closed: "已关闭",
};

export function getTopicStatusLabel(status: TopicStatus) {
  return topicStatusLabels[status];
}

export function buildTopicCapacityLabel(
  topic: Pick<Topic, "selectedCount" | "capacity">,
) {
  return `${topic.selectedCount} / ${topic.capacity} 人`;
}

export function getTopicKeywordGroups(
  topic: Pick<Topic, "techKeywords" | "portrait">,
) {
  return {
    primary: topic.techKeywords,
    derived: topic.portrait?.keywords ?? [],
  };
}
