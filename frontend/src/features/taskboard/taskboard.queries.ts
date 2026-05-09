import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createMilestone,
  deleteMilestone,
  getMilestones,
  updateMilestone,
} from "@/features/taskboard/taskboard.api";
import type {
  CreateMilestoneRequest,
  MilestoneListParams,
  PatchMilestoneRequest,
} from "@/features/taskboard/taskboard.types";

export const taskboardKeys = {
  all: ["taskboard"] as const,
  milestones: (params: MilestoneListParams) =>
    [
      ...taskboardKeys.all,
      "milestones",
      params.studentId ?? "",
      params.fromDate ?? "",
      params.toDate ?? "",
      params.page ?? 1,
      params.pageSize ?? 50,
    ] as const,
};

export function useMilestonesQuery(
  enabled: boolean,
  params: MilestoneListParams = {},
) {
  return useQuery({
    queryKey: taskboardKeys.milestones(params),
    queryFn: () => getMilestones(params),
    enabled,
  });
}

export function useCreateMilestoneMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateMilestoneRequest) => createMilestone(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: taskboardKeys.all });
    },
  });
}

export function useUpdateMilestoneMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      milestoneId,
      payload,
    }: {
      milestoneId: string;
      payload: PatchMilestoneRequest;
    }) => updateMilestone(milestoneId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: taskboardKeys.all });
    },
  });
}

export function useDeleteMilestoneMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (milestoneId: string) => deleteMilestone(milestoneId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: taskboardKeys.all });
    },
  });
}
