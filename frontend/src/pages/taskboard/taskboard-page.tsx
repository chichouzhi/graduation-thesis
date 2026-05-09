import { useState } from "react";

import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAssignmentsQuery } from "@/features/selection/selection.queries";
import {
  useCreateMilestoneMutation,
  useDeleteMilestoneMutation,
  useMilestonesQuery,
  useUpdateMilestoneMutation,
} from "@/features/taskboard/taskboard.queries";
import type { Milestone, MilestoneStatus } from "@/features/taskboard/taskboard.types";
import {
  buildMilestoneColumns,
  buildMilestoneSummary,
  getMilestoneDateRangeLabel,
  getMilestoneStatusLabel,
} from "@/features/taskboard/taskboard.utils";
import { getErrorMessage } from "@/lib/api-error";
import {
  buildCreateMilestoneRequest,
  buildPatchMilestoneStatusRequest,
  initialMilestoneDraft,
  type MilestoneDraft,
} from "@/pages/taskboard/taskboard-page.utils";

function getNextStatus(status: MilestoneStatus): MilestoneStatus {
  switch (status) {
    case "todo":
      return "doing";
    case "doing":
      return "done";
    case "done":
      return "todo";
  }
}

function getNextStatusActionLabel(status: MilestoneStatus) {
  switch (status) {
    case "todo":
      return "开始推进";
    case "doing":
      return "标记完成";
    case "done":
      return "重新待办";
  }
}

function MilestoneCard({
  milestone,
  isMutating,
  onDelete,
  onStatusChange,
}: {
  milestone: Milestone;
  isMutating: boolean;
  onDelete: (milestoneId: string) => void;
  onStatusChange: (milestoneId: string, status: MilestoneStatus) => void;
}) {
  const nextStatus = getNextStatus(milestone.status);

  return (
    <div className="task-card">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 12,
          alignItems: "flex-start",
        }}
      >
        <h4 className="task-title">{milestone.title}</h4>
        <span className={`badge ${milestone.status}`}>
          {getMilestoneStatusLabel(milestone.status)}
        </span>
      </div>

      {milestone.description ? (
        <p className="muted small" style={{ marginTop: 10, lineHeight: 1.8 }}>
          {milestone.description}
        </p>
      ) : null}

      <p className="muted small" style={{ marginTop: 10 }}>
        时间：{getMilestoneDateRangeLabel(milestone)}
      </p>
      <p className="muted small" style={{ marginTop: 6 }}>
        排序：{milestone.sortOrder}
      </p>

      {milestone.isOverdue ? (
        <div style={{ marginTop: 12 }}>
          <span className="badge failed">已逾期</span>
        </div>
      ) : null}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 16 }}>
        <Button
          variant="outline"
          onClick={() => onStatusChange(milestone.id, nextStatus)}
          disabled={isMutating}
        >
          {getNextStatusActionLabel(milestone.status)}
        </Button>
        <Button
          variant="outline"
          onClick={() => onDelete(milestone.id)}
          disabled={isMutating}
        >
          删除
        </Button>
      </div>
    </div>
  );
}

export function TaskboardPage() {
  const [draft, setDraft] = useState<MilestoneDraft>(initialMilestoneDraft);
  const [operationError, setOperationError] = useState("");
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string | null>(null);

  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const currentTerm = useAppStore((state) => state.currentTerm);
  const currentUser = useAppStore((state) => state.currentUser);

  const assignmentsQuery = useAssignmentsQuery(isAuthenticated);
  const assignments = assignmentsQuery.data?.items ?? [];
  const selectedAssignment =
    assignments.find((assignment) => assignment.id === selectedAssignmentId) ??
    assignments[0] ??
    null;
  const milestoneStudentId = selectedAssignment?.studentId;
  const milestonesQuery = useMilestonesQuery(isAuthenticated, {
    studentId: milestoneStudentId,
  });
  const createMilestoneMutation = useCreateMilestoneMutation();
  const updateMilestoneMutation = useUpdateMilestoneMutation();
  const deleteMilestoneMutation = useDeleteMilestoneMutation();
  const milestones = milestonesQuery.data?.items ?? [];
  const columns = buildMilestoneColumns(milestones);
  const summary = buildMilestoneSummary(milestones);
  const isMutating =
    createMilestoneMutation.isPending ||
    updateMilestoneMutation.isPending ||
    deleteMilestoneMutation.isPending;

  async function handleCreateMilestone() {
    if (!draft.title.trim() || createMilestoneMutation.isPending) {
      return;
    }

    setOperationError("");

    try {
      await createMilestoneMutation.mutateAsync(buildCreateMilestoneRequest(draft));
      setDraft(initialMilestoneDraft);
    } catch (error) {
      setOperationError(getErrorMessage(error, "里程碑创建失败，请稍后重试。"));
    }
  }

  async function handleStatusChange(milestoneId: string, status: MilestoneStatus) {
    setOperationError("");

    try {
      await updateMilestoneMutation.mutateAsync({
        milestoneId,
        payload: buildPatchMilestoneStatusRequest(status),
      });
    } catch (error) {
      setOperationError(getErrorMessage(error, "任务状态更新失败，请稍后重试。"));
    }
  }

  async function handleDeleteMilestone(milestoneId: string) {
    setOperationError("");

    try {
      await deleteMilestoneMutation.mutateAsync(milestoneId);
    } catch (error) {
      setOperationError(getErrorMessage(error, "任务删除失败，请稍后重试。"));
    }
  }

  return (
    <div className="page-stack">
      <PageSection className="hero-section">
        <p className="kicker">Task Progress</p>
        <h2 className="hero-title">毕业过程任务管理</h2>
        <p className="hero-copy">
          按待办、进行中和已完成三个状态维护毕业设计任务，结合截止时间和逾期标记持续跟踪开题、实现、论文与答辩准备进度。
        </p>
      </PageSection>

      <PageSection className="paper">
        <SectionHeading
          title="指导课题"
          description="老师接受志愿后形成的指导关系会在这里作为任务看板上下文。"
        />

        {assignmentsQuery.isLoading ? (
          <div style={{ marginTop: 22 }}>
            <EmptyState title="正在加载指导关系" description="系统正在同步已确认的选题关系。" />
          </div>
        ) : assignmentsQuery.isError ? (
          <div style={{ marginTop: 22 }}>
            <EmptyState title="指导关系加载失败" description="暂时无法获取师生课题关系。" />
          </div>
        ) : selectedAssignment ? (
          <div className="detail-card" style={{ marginTop: 22 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 16,
                alignItems: "flex-start",
                flexWrap: "wrap",
              }}
            >
              <div>
                <h3>{selectedAssignment.topicTitle ?? selectedAssignment.topicId}</h3>
                <p className="muted small" style={{ marginTop: 10, lineHeight: 1.9 }}>
                  学生：{selectedAssignment.studentName ?? selectedAssignment.studentId} · 状态：
                  {selectedAssignment.status === "active" ? "已确认指导" : "已取消"}
                </p>
                <p className="muted small" style={{ marginTop: 8, lineHeight: 1.9 }}>
                  当前任务列表按学生 ID {selectedAssignment.studentId} 查询。
                </p>
              </div>

              {assignments.length > 1 ? (
                <div className="field" style={{ minWidth: 260 }}>
                  <label htmlFor="assignment-selector">切换指导关系</label>
                  <select
                    id="assignment-selector"
                    className="upload-select"
                    value={selectedAssignment.id}
                    onChange={(event) => setSelectedAssignmentId(event.target.value)}
                  >
                    {assignments.map((assignment) => (
                      <option key={assignment.id} value={assignment.id}>
                        {assignment.topicTitle ?? assignment.topicId}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
            </div>
          </div>
        ) : (
          <div style={{ marginTop: 22 }}>
            <EmptyState
              title="暂无指导关系"
              description="接受学生志愿后，任务看板会自动按对应学生查看毕业过程任务。"
            />
          </div>
        )}
      </PageSection>

      <div className="grid-3">
        <div className="detail-card">
          <p style={{ fontWeight: 600 }}>总任务</p>
          <p className="muted small" style={{ marginTop: 10 }}>
            {summary.total} 项，来自
            {selectedAssignment
              ? selectedAssignment.studentName ?? selectedAssignment.studentId
              : "当前用户"}
            的里程碑列表。
          </p>
        </div>
        <div className="detail-card">
          <p style={{ fontWeight: 600 }}>进行中</p>
          <p className="muted small" style={{ marginTop: 10 }}>
            {summary.doing} 项，适合答辩前每日跟进。
          </p>
        </div>
        <div className="detail-card">
          <p style={{ fontWeight: 600 }}>风险提醒</p>
          <p className="muted small" style={{ marginTop: 10 }}>
            {summary.overdue} 项逾期，{summary.done} 项已完成。
          </p>
        </div>
      </div>

      <PageSection className="paper">
        <SectionHeading
          title="毕业任务看板"
          description={`当前学期：${currentTerm.name} · 当前用户：${currentUser?.display_name ?? currentUser?.username ?? "未登录"}`}
        />

        <div className="form-stack" style={{ marginTop: 22 }}>
          <div className="grid-2">
            <div className="field">
              <label htmlFor="milestone-title">任务标题</label>
              <Input
                id="milestone-title"
                value={draft.title}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, title: event.target.value }))
                }
                placeholder="例如：补充答辩演示材料"
              />
            </div>
            <div className="field">
              <label htmlFor="milestone-status">任务状态</label>
              <select
                id="milestone-status"
                className="upload-select"
                value={draft.status}
                onChange={(event) =>
                  setDraft((current) => ({
                    ...current,
                    status: event.target.value as MilestoneStatus,
                  }))
                }
              >
                <option value="todo">待办</option>
                <option value="doing">进行中</option>
                <option value="done">已完成</option>
              </select>
            </div>
          </div>

          <div className="field">
            <label htmlFor="milestone-description">任务说明</label>
            <Textarea
              id="milestone-description"
              value={draft.description}
              onChange={(event) =>
                setDraft((current) => ({ ...current, description: event.target.value }))
              }
              placeholder="说明这个阶段任务要产出什么材料或验证结果。"
            />
          </div>

          <div className="grid-3">
            <div className="field">
              <label htmlFor="milestone-start-date">开始日期</label>
              <Input
                id="milestone-start-date"
                type="date"
                value={draft.startDate}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, startDate: event.target.value }))
                }
              />
            </div>
            <div className="field">
              <label htmlFor="milestone-end-date">截止日期</label>
              <Input
                id="milestone-end-date"
                type="date"
                value={draft.endDate}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, endDate: event.target.value }))
                }
              />
            </div>
            <div className="field">
              <label htmlFor="milestone-sort-order">排序</label>
              <Input
                id="milestone-sort-order"
                value={draft.sortOrder}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, sortOrder: event.target.value }))
                }
                placeholder="例如：0"
              />
            </div>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            <Button
              onClick={() => void handleCreateMilestone()}
              disabled={!draft.title.trim() || createMilestoneMutation.isPending}
            >
              创建里程碑
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setDraft(initialMilestoneDraft);
                setOperationError("");
              }}
            >
              清空输入
            </Button>
          </div>
        </div>

        {operationError ? (
          <p className="small" style={{ marginTop: 12, color: "var(--danger-foreground)" }}>
            {operationError}
          </p>
        ) : null}

        {milestonesQuery.isLoading ? (
          <div style={{ marginTop: 22 }}>
            <EmptyState
              title="正在加载任务"
              description="系统正在同步毕业设计里程碑，请稍候。"
            />
          </div>
        ) : null}

        {milestonesQuery.isError ? (
          <div style={{ marginTop: 22 }}>
            <EmptyState
              title="任务看板加载失败"
              description={getErrorMessage(milestonesQuery.error, "暂时无法获取里程碑列表。")}
              action={
                <Button variant="outline" onClick={() => void milestonesQuery.refetch()}>
                  重试
                </Button>
              }
            />
          </div>
        ) : null}

        {!milestonesQuery.isLoading && !milestonesQuery.isError && !milestones.length ? (
          <div style={{ marginTop: 22 }}>
            <EmptyState
              title="暂无任务"
              description="当前还没有毕业设计里程碑。后续可在这里继续接入创建和状态更新。"
            />
          </div>
        ) : null}
      </PageSection>

      {!milestonesQuery.isLoading && !milestonesQuery.isError && milestones.length ? (
        <div className="task-column-list">
          {columns.map((column) => (
            <section key={column.id} className="task-column">
              <div className="column-header">
                <div>
                  <h3>{column.title}</h3>
                  <p className="muted small" style={{ marginTop: 8 }}>
                    {column.description}
                  </p>
                </div>
                <span className="priority-pill">{column.items.length} 项</span>
              </div>

              <div style={{ display: "grid", gap: 14, marginTop: 18 }}>
                {column.items.length ? (
                  column.items.map((milestone) => (
                    <MilestoneCard
                      key={milestone.id}
                      milestone={milestone}
                      isMutating={isMutating}
                      onDelete={(milestoneId) => void handleDeleteMilestone(milestoneId)}
                      onStatusChange={(milestoneId, status) =>
                        void handleStatusChange(milestoneId, status)
                      }
                    />
                  ))
                ) : (
                  <EmptyState
                    title="暂无任务"
                    description={`当前没有${column.title}状态的任务。`}
                  />
                )}
              </div>
            </section>
          ))}
        </div>
      ) : null}
    </div>
  );
}
