export type ApplicationFlowStatus =
  | "pending"
  | "withdrawn"
  | "accepted"
  | "rejected"
  | "superseded";

export type ApplicationPriority = 1 | 2;

export type ApplicationDecisionAction = "accept" | "reject";

export type AssignmentStatus = "active" | "cancelled";

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

export type AssignmentDto = {
  id: string;
  student_id: string;
  student_name?: string | null;
  teacher_id: string;
  topic_id: string;
  topic_title?: string | null;
  term_id: string;
  application_id?: string | null;
  status: AssignmentStatus;
  confirmed_at?: string | null;
};

export type Assignment = {
  id: string;
  studentId: string;
  studentName: string | null;
  teacherId: string;
  topicId: string;
  topicTitle: string | null;
  termId: string;
  applicationId: string | null;
  status: AssignmentStatus;
  confirmedAt: string | null;
};

export type ApplicationListParams = {
  termId?: string;
  topicId?: string;
  page?: number;
  pageSize?: number;
};

export type AssignmentListParams = {
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

export type ApplicationDecisionRequest = {
  action: ApplicationDecisionAction;
  comment?: string;
};

export type ApplicationDecisionDto = {
  application: ApplicationDto;
  assignment: AssignmentDto | null;
};

export type ApplicationDecision = {
  application: Application;
  assignment: Assignment | null;
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

export function mapAssignmentDto(assignment: AssignmentDto): Assignment {
  return {
    id: assignment.id,
    studentId: assignment.student_id,
    studentName: assignment.student_name ?? null,
    teacherId: assignment.teacher_id,
    topicId: assignment.topic_id,
    topicTitle: assignment.topic_title ?? null,
    termId: assignment.term_id,
    applicationId: assignment.application_id ?? null,
    status: assignment.status,
    confirmedAt: assignment.confirmed_at ?? null,
  };
}

export function mapApplicationDecisionDto(
  decision: ApplicationDecisionDto,
): ApplicationDecision {
  return {
    application: mapApplicationDto(decision.application),
    assignment: decision.assignment ? mapAssignmentDto(decision.assignment) : null,
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
