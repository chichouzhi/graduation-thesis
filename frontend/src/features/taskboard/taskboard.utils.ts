import type { Milestone, MilestoneStatus } from "@/features/taskboard/taskboard.types";

export const milestoneColumns: Array<{ id: MilestoneStatus; title: string; description: string }> = [
  {
    id: "todo",
    title: "待办",
    description: "尚未启动的毕业设计任务。",
  },
  {
    id: "doing",
    title: "进行中",
    description: "当前正在推进的实现、论文或答辩准备任务。",
  },
  {
    id: "done",
    title: "已完成",
    description: "已经完成并可作为过程材料沉淀的任务。",
  },
];

export function getMilestoneStatusLabel(status: MilestoneStatus) {
  switch (status) {
    case "todo":
      return "待办";
    case "doing":
      return "进行中";
    case "done":
      return "已完成";
  }
}

export function formatDateLabel(date?: string | null) {
  if (!date) {
    return "未设置";
  }

  const [year, month, day] = date.split("-");

  if (!year || !month || !day) {
    return date;
  }

  return `${year}年${Number(month)}月${Number(day)}日`;
}

export function getMilestoneDateRangeLabel(milestone: Pick<Milestone, "startDate" | "endDate">) {
  if (!milestone.startDate && !milestone.endDate) {
    return "未设置日期";
  }

  if (!milestone.startDate) {
    return `截止 ${formatDateLabel(milestone.endDate)}`;
  }

  if (!milestone.endDate) {
    return `开始 ${formatDateLabel(milestone.startDate)}`;
  }

  return `${formatDateLabel(milestone.startDate)} - ${formatDateLabel(milestone.endDate)}`;
}

export function sortMilestones(milestones: Milestone[]) {
  return [...milestones].sort((left, right) => {
    if (left.sortOrder !== right.sortOrder) {
      return left.sortOrder - right.sortOrder;
    }

    return (
      (left.endDate ?? "9999-12-31").localeCompare(right.endDate ?? "9999-12-31") ||
      left.createdAt.localeCompare(right.createdAt)
    );
  });
}

export function buildMilestoneColumns(milestones: Milestone[]) {
  const sorted = sortMilestones(milestones);

  return milestoneColumns.map((column) => ({
    ...column,
    items: sorted.filter((milestone) => milestone.status === column.id),
  }));
}

export function buildMilestoneSummary(milestones: Milestone[]) {
  return {
    total: milestones.length,
    doing: milestones.filter((milestone) => milestone.status === "doing").length,
    done: milestones.filter((milestone) => milestone.status === "done").length,
    overdue: milestones.filter((milestone) => milestone.isOverdue).length,
  };
}
