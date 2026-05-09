import { apiClient } from "@/lib/axios";
import type {
  Application,
  ApplicationDto,
  ApplicationListParams,
  CreateApplicationRequest,
  PaginatedResponseDto,
  PatchApplicationRequest,
} from "@/features/selection/selection.types";
import {
  mapApplicationDto,
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

export async function deleteApplication(applicationId: string) {
  await apiClient.delete(`/applications/${applicationId}`);
}
