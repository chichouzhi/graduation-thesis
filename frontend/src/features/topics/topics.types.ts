import type { AsyncStatus } from "@/types/app";

export type TopicStatus = "draft" | "pending_review" | "published" | "rejected" | "closed";
export type TopicDifficultyLabel = "basic" | "intermediate" | "advanced";
export type RecommendationCapacityStatus = "available" | "nearly_full" | "full";

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
  difficulty_label?: TopicDifficultyLabel | null;
  difficulty_reason?: string | null;
  required_capabilities?: string[];
  suitable_students?: string[];
  risks?: string[];
  summary?: string | null;
  extracted_at?: string | null;
} | null;

export type TopicPortrait = {
  keywords: string[];
  difficultyLabel: TopicDifficultyLabel | null;
  difficultyReason: string | null;
  requiredCapabilities: string[];
  suitableStudents: string[];
  risks: string[];
  summary: string | null;
  extractedAt: string | null;
} | null;

export type RecommendationExplainDto = {
  matched_skills?: string[];
  matched_keywords?: string[];
  matched_capabilities?: string[];
  difficulty_fit?: string | null;
  capacity_status?: RecommendationCapacityStatus | null;
  warnings?: string[];
  reasons?: string[];
} | null;

export type RecommendationTopicItemDto = {
  topic_id: string;
  title: string;
  score: number;
  explain?: RecommendationExplainDto;
};

export type RecommendationTopicListDto = {
  items: RecommendationTopicItemDto[];
  top_n: number;
};

export type RecommendationExplain = {
  matchedSkills: string[];
  matchedKeywords: string[];
  matchedCapabilities: string[];
  difficultyFit: string | null;
  capacityStatus: RecommendationCapacityStatus | null;
  warnings: string[];
  reasons: string[];
} | null;

export type RecommendationTopicItem = {
  topicId: string;
  title: string;
  score: number;
  explain?: RecommendationExplain;
};

export type RecommendationTopicList = {
  items: RecommendationTopicItem[];
  topN: number;
};

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
    difficultyLabel: portrait.difficulty_label ?? null,
    difficultyReason: portrait.difficulty_reason ?? null,
    requiredCapabilities: portrait.required_capabilities ?? [],
    suitableStudents: portrait.suitable_students ?? [],
    risks: portrait.risks ?? [],
    summary: portrait.summary ?? null,
    extractedAt: portrait.extracted_at ?? null,
  };
}

export function mapRecommendationTopicListDto(
  response: RecommendationTopicListDto,
): RecommendationTopicList {
  return {
    topN: response.top_n,
    items: response.items.map((item) => ({
      topicId: item.topic_id,
      title: item.title,
      score: item.score,
      explain: item.explain
        ? {
            matchedSkills: item.explain.matched_skills ?? [],
            matchedKeywords: item.explain.matched_keywords ?? [],
            matchedCapabilities: item.explain.matched_capabilities ?? [],
            difficultyFit: item.explain.difficulty_fit ?? null,
            capacityStatus: item.explain.capacity_status ?? null,
            warnings: item.explain.warnings ?? [],
            reasons: item.explain.reasons ?? [],
          }
        : null,
    })),
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
