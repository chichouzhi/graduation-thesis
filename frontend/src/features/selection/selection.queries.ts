import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createApplication,
  decideApplication,
  deleteApplication,
  getApplications,
  updateApplication,
} from "@/features/selection/selection.api";
import type {
  ApplicationDecisionRequest,
  ApplicationListParams,
  CreateApplicationRequest,
  PatchApplicationRequest,
} from "@/features/selection/selection.types";

export const selectionKeys = {
  all: ["selection"] as const,
  applications: (params: ApplicationListParams) =>
    [
      ...selectionKeys.all,
      "applications",
      params.termId ?? "",
      params.topicId ?? "",
      params.page ?? 1,
      params.pageSize ?? 50,
    ] as const,
};

export function useApplicationsQuery(
  enabled: boolean,
  params: ApplicationListParams = {},
) {
  return useQuery({
    queryKey: selectionKeys.applications(params),
    queryFn: () => getApplications(params),
    enabled,
  });
}

export function useCreateApplicationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateApplicationRequest) => createApplication(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: selectionKeys.all });
    },
  });
}

export function useUpdateApplicationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      applicationId,
      payload,
    }: {
      applicationId: string;
      payload: PatchApplicationRequest;
    }) => updateApplication(applicationId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: selectionKeys.all });
    },
  });
}

export function useDecideApplicationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      applicationId,
      payload,
    }: {
      applicationId: string;
      payload: ApplicationDecisionRequest;
    }) => decideApplication(applicationId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: selectionKeys.all });
    },
  });
}

export function useDeleteApplicationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (applicationId: string) => deleteApplication(applicationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: selectionKeys.all });
    },
  });
}
