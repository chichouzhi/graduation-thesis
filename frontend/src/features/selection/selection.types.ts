export type ApplicationFlowStatus =
  | "pending"
  | "withdrawn"
  | "accepted"
  | "rejected"
  | "superseded";

export type ApplicationPriority = 1 | 2;

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

export type ApplicationDto = {
  id: string;
  topic_id: string;
  topic_title?: string | null;
  student_id: string;
  term_id: string;
  priority: ApplicationPriority;
  status: ApplicationFlowStatus;
  created_at: string;
  updated_at?: string | null;
};

export type Application = {
  id: string;
  topicId: string;
  topicTitle: string | null;
  studentId: string;
  termId: string;
  priority: ApplicationPriority;
  status: ApplicationFlowStatus;
  createdAt: string;
  updatedAt: string | null;
};

export type ApplicationListParams = {
  termId?: string;
  topicId?: string;
  page?: number;
  pageSize?: number;
};

export type CreateApplicationRequest = {
  topic_id: string;
  term_id: string;
  priority: ApplicationPriority;
};

export type PatchApplicationRequest = {
  priority?: ApplicationPriority;
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

export function mapApplicationDto(application: ApplicationDto): Application {
  return {
    id: application.id,
    topicId: application.topic_id,
    topicTitle: application.topic_title ?? null,
    studentId: application.student_id,
    termId: application.term_id,
    priority: application.priority,
    status: application.status,
    createdAt: application.created_at,
    updatedAt: application.updated_at ?? null,
  };
}

export function buildCreateApplicationRequest(
  topicId: string,
  termId: string,
  priority: ApplicationPriority,
): CreateApplicationRequest {
  return {
    topic_id: topicId,
    term_id: termId,
    priority,
  };
}
