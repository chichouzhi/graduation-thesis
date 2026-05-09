export type MilestoneStatus = "todo" | "doing" | "done";

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

export type MilestoneDto = {
  id: string;
  student_id: string;
  title: string;
  description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  status: MilestoneStatus;
  sort_order?: number | null;
  is_overdue?: boolean | null;
  created_at: string;
  updated_at?: string | null;
};

export type Milestone = {
  id: string;
  studentId: string;
  title: string;
  description: string | null;
  startDate: string | null;
  endDate: string | null;
  status: MilestoneStatus;
  sortOrder: number;
  isOverdue: boolean;
  createdAt: string;
  updatedAt: string | null;
};

export type MilestoneListParams = {
  studentId?: string;
  fromDate?: string;
  toDate?: string;
  page?: number;
  pageSize?: number;
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

export function mapMilestoneDto(milestone: MilestoneDto): Milestone {
  return {
    id: milestone.id,
    studentId: milestone.student_id,
    title: milestone.title,
    description: milestone.description ?? null,
    startDate: milestone.start_date ?? null,
    endDate: milestone.end_date ?? null,
    status: milestone.status,
    sortOrder: milestone.sort_order ?? 0,
    isOverdue: milestone.is_overdue ?? false,
    createdAt: milestone.created_at,
    updatedAt: milestone.updated_at ?? null,
  };
}
