import { useQuery } from "@tanstack/react-query";

import { getTopic, getTopics } from "@/features/topics/topics.api";
import type { Topic } from "@/features/topics/topics.types";

export const topicKeys = {
  all: ["topics"] as const,
  list: (termId: string) => [...topicKeys.all, "list", termId] as const,
  detail: (topicId: string) => [...topicKeys.all, "detail", topicId] as const,
};

export function useTopicsQuery(enabled: boolean, termId: string) {
  return useQuery({
    queryKey: topicKeys.list(termId),
    queryFn: () => getTopics(termId),
    enabled,
  });
}

export function useTopicQuery(topicId: string | null, enabled: boolean) {
  return useQuery<Topic>({
    queryKey: topicId ? topicKeys.detail(topicId) : [...topicKeys.all, "detail", "empty"],
    queryFn: async () => getTopic(topicId!),
    enabled: enabled && Boolean(topicId),
  });
}
