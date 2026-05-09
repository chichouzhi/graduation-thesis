import { useQuery } from "@tanstack/react-query";

import { getMilestones } from "@/features/taskboard/taskboard.api";
import type { MilestoneListParams } from "@/features/taskboard/taskboard.types";

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
