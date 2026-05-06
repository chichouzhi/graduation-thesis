import { apiClient } from "@/lib/axios";
import type {
  PaginatedResponseDto,
  TopicDto,
} from "@/features/topics/topics.types";
import {
  mapPaginatedResponseDto,
  mapTopicDto,
} from "@/features/topics/topics.types";

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
