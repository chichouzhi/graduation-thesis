import { apiClient } from "@/lib/axios";
import type {
  PaginatedResponseDto,
  RecommendationTopicListDto,
  TopicDto,
} from "@/features/topics/topics.types";
import {
  mapPaginatedResponseDto,
  mapRecommendationTopicListDto,
  mapTopicDto,
} from "@/features/topics/topics.types";

export type CreateTopicPayload = {
  title: string;
  summary: string;
  requirements: string;
  tech_keywords: string[];
  capacity: number;
  term_id: string;
};

export type PatchTopicPayload = {
  title?: string;
  summary?: string;
  requirements?: string;
  tech_keywords?: string[];
  capacity?: number;
};

export async function getTopics(termId: string) {
  const response = await apiClient.get<PaginatedResponseDto<TopicDto>>("/topics", {
    params: {
      term_id: termId,
      page: 1,
      page_size: 50,
    },
  });

  return mapPaginatedResponseDto(response.data, mapTopicDto);
}

export async function getTopic(topicId: string) {
  const response = await apiClient.get<TopicDto>(`/topics/${topicId}`);
  return mapTopicDto(response.data);
}

export async function createTopic(payload: CreateTopicPayload) {
  const response = await apiClient.post<TopicDto>("/topics", payload);
  return mapTopicDto(response.data);
}

export async function updateTopic(topicId: string, payload: PatchTopicPayload) {
  const response = await apiClient.patch<TopicDto>(`/topics/${topicId}`, payload);
  return mapTopicDto(response.data);
}

export async function getTopicRecommendations(termId: string, topN = 10) {
  const response = await apiClient.get<RecommendationTopicListDto>("/recommendations/topics", {
    params: {
      term_id: termId,
      top_n: topN,
      explain: true,
    },
  });

  return mapRecommendationTopicListDto(response.data);
}
