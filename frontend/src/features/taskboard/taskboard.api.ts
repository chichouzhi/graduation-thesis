import { apiClient } from "@/lib/axios";
import type {
  Milestone,
  MilestoneDto,
  MilestoneListParams,
  PaginatedResponseDto,
} from "@/features/taskboard/taskboard.types";
import {
  mapMilestoneDto,
  mapPaginatedResponseDto,
} from "@/features/taskboard/taskboard.types";

export async function getMilestones(params: MilestoneListParams = {}) {
  const response = await apiClient.get<PaginatedResponseDto<MilestoneDto>>("/milestones", {
    params: {
      student_id: params.studentId,
      from_date: params.fromDate,
      to_date: params.toDate,
      page: params.page ?? 1,
      page_size: params.pageSize ?? 50,
    },
  });

  return mapPaginatedResponseDto<MilestoneDto, Milestone>(
    response.data,
    mapMilestoneDto,
  );
}
