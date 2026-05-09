import { apiClient } from "@/lib/axios";
import type {
  Application,
  ApplicationDecisionDto,
  ApplicationDecisionRequest,
  ApplicationDto,
  ApplicationListParams,
  Assignment,
  AssignmentDto,
  AssignmentListParams,
  CreateApplicationRequest,
  PaginatedResponseDto,
  PatchApplicationRequest,
} from "@/features/selection/selection.types";
import {
  mapApplicationDto,
  mapApplicationDecisionDto,
  mapAssignmentDto,
  mapPaginatedResponseDto,
} from "@/features/selection/selection.types";

export async function getApplications(params: ApplicationListParams = {}) {
  const response = await apiClient.get<PaginatedResponseDto<ApplicationDto>>("/applications", {
    params: {
      term_id: params.termId,
      topic_id: params.topicId,
      page: params.page ?? 1,
      page_size: params.pageSize ?? 50,
    },
  });

  return mapPaginatedResponseDto<ApplicationDto, Application>(
    response.data,
    mapApplicationDto,
  );
}

export async function getAssignments(params: AssignmentListParams = {}) {
  const response = await apiClient.get<PaginatedResponseDto<AssignmentDto>>("/assignments", {
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 50,
    },
  });

  return mapPaginatedResponseDto<AssignmentDto, Assignment>(
    response.data,
    mapAssignmentDto,
  );
}

export async function createApplication(payload: CreateApplicationRequest) {
  const response = await apiClient.post<ApplicationDto>("/applications", payload);
  return mapApplicationDto(response.data);
}

export async function updateApplication(
  applicationId: string,
  payload: PatchApplicationRequest,
) {
  const response = await apiClient.patch<ApplicationDto>(
    `/applications/${applicationId}`,
    payload,
  );
  return mapApplicationDto(response.data);
}

export async function decideApplication(
  applicationId: string,
  payload: ApplicationDecisionRequest,
) {
  const response = await apiClient.post<ApplicationDecisionDto>(
    `/applications/${applicationId}/decisions`,
    payload,
  );

  return mapApplicationDecisionDto(response.data);
}

export async function deleteApplication(applicationId: string) {
  await apiClient.delete(`/applications/${applicationId}`);
}
