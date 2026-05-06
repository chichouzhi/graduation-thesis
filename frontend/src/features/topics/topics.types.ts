import type { AsyncStatus } from "@/types/app";

export type TopicStatus = "draft" | "pending_review" | "published" | "rejected" | "closed";

export type PaginatedResponseDto<T> = {
  page: number;
  page_size: number;
  total: number;
  items: T[];
};

export type PaginatedResponse<T> = {
  page: number;
  pageSize: number;
  total: number;
  items: T[];
};

export type TopicPortraitDto = {
  keywords?: string[];
  extracted_at?: string | null;
} | null;

export type TopicPortrait = {
  keywords: string[];
  extractedAt?: string | null;
} | null;

export type TopicDto = {
  id: string;
  title: string;
  summary: string;
  requirements: string;
  tech_keywords?: string[];
  capacity: number;
  selected_count: number;
  teacher_id: string;
  term_id: string;
  status: TopicStatus;
  portrait?: TopicPortraitDto;
  llm_keyword_job_id?: string | null;
  llm_keyword_job_status?: AsyncStatus | null;
  created_at: string;
  updated_at: string;
};

export type Topic = {
  id: string;
  title: string;
  summary: string;
  requirements: string;
  techKeywords: string[];
  capacity: number;
  selectedCount: number;
  teacherId: string;
  termId: string;
  status: TopicStatus;
  portrait?: TopicPortrait;
  llmKeywordJobId?: string | null;
  llmKeywordJobStatus?: AsyncStatus | null;
  createdAt: string;
  updatedAt: string;
};

export function mapPaginatedResponseDto<TDto, TModel>(
  response: PaginatedResponseDto<TDto>,
  mapItem: (item: TDto) => TModel,
): PaginatedResponse<TModel> {
  return {
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
    items: response.items.map(mapItem),
  };
}

export function mapTopicPortraitDto(
  portrait?: TopicPortraitDto,
): TopicPortrait | undefined {
  if (portrait === undefined) {
    return undefined;
  }

  if (portrait === null) {
    return null;
  }

  return {
    keywords: portrait.keywords ?? [],
    extractedAt: portrait.extracted_at,
  };
}

export function mapTopicDto(topic: TopicDto): Topic {
  return {
    id: topic.id,
    title: topic.title,
    summary: topic.summary,
    requirements: topic.requirements,
    techKeywords: topic.tech_keywords ?? [],
    capacity: topic.capacity,
    selectedCount: topic.selected_count,
    teacherId: topic.teacher_id,
    termId: topic.term_id,
    status: topic.status,
    portrait: mapTopicPortraitDto(topic.portrait),
    llmKeywordJobId: topic.llm_keyword_job_id,
    llmKeywordJobStatus: topic.llm_keyword_job_status,
    createdAt: topic.created_at,
    updatedAt: topic.updated_at,
  };
}
