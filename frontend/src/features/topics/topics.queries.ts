import { useMutation, useQuery } from "@tanstack/react-query";

import {
  createTopic,
  getTopic,
  getTopicRecommendations,
  getTopics,
  updateTopic,
} from "@/features/topics/topics.api";
import type { Topic } from "@/features/topics/topics.types";
import type { AsyncStatus } from "@/types/app";

export const topicKeys = {
  all: ["topics"] as const,
  list: (termId: string) => [...topicKeys.all, "list", termId] as const,
  detail: (topicId: string) => [...topicKeys.all, "detail", topicId] as const,
  recommendations: (termId: string, topN: number) =>
    [...topicKeys.all, "recommendations", termId, topN] as const,
};

export function getTopicPollingInterval(status?: AsyncStatus | null) {
  return status === "pending" || status === "running" ? 2000 : false;
}

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
    refetchInterval: (query) => getTopicPollingInterval(query.state.data?.llmKeywordJobStatus),
  });
}

export function useCreateTopicMutation() {
  return useMutation({
    mutationFn: createTopic,
  });
}

export function useUpdateTopicMutation() {
  return useMutation({
    mutationFn: ({ topicId, payload }: { topicId: string; payload: Parameters<typeof updateTopic>[1] }) =>
      updateTopic(topicId, payload),
  });
}

export function useTopicRecommendationsQuery(
  termId: string,
  enabled: boolean,
  topN = 10,
) {
  return useQuery({
    queryKey: topicKeys.recommendations(termId, topN),
    queryFn: () => getTopicRecommendations(termId, topN),
    enabled,
  });
}
