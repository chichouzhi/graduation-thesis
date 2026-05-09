import { apiClient } from "@/lib/axios";
import type {
  CreateMilestoneRequest,
  Milestone,
  MilestoneDto,
  MilestoneListParams,
  PaginatedResponseDto,
  PatchMilestoneRequest,
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

export async function createMilestone(payload: CreateMilestoneRequest) {
  const response = await apiClient.post<MilestoneDto>("/milestones", payload);
  return mapMilestoneDto(response.data);
}

export async function updateMilestone(
  milestoneId: string,
  payload: PatchMilestoneRequest,
) {
  const response = await apiClient.patch<MilestoneDto>(
    `/milestones/${milestoneId}`,
    payload,
  );
  return mapMilestoneDto(response.data);
}

export async function deleteMilestone(milestoneId: string) {
  await apiClient.delete(`/milestones/${milestoneId}`);
}
