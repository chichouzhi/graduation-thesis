import type {
  CreateMilestoneRequest,
  MilestoneStatus,
  PatchMilestoneRequest,
} from "@/features/taskboard/taskboard.types";

export type MilestoneDraft = {
  title: string;
  description: string;
  startDate: string;
  endDate: string;
  status: MilestoneStatus;
  sortOrder: string;
};

export const initialMilestoneDraft: MilestoneDraft = {
  title: "",
  description: "",
  startDate: "",
  endDate: "",
  status: "todo",
  sortOrder: "0",
};

export function buildCreateMilestoneRequest(
  draft: MilestoneDraft,
): CreateMilestoneRequest {
  const sortOrder = Number(draft.sortOrder.trim());

  return {
    title: draft.title.trim(),
    description: draft.description.trim() || null,
    start_date: draft.startDate,
    end_date: draft.endDate,
    status: draft.status,
    sort_order: Number.isFinite(sortOrder) ? sortOrder : 0,
  };
}

export function buildPatchMilestoneStatusRequest(
  status: MilestoneStatus,
): PatchMilestoneRequest {
  return { status };
}
