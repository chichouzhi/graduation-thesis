import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import { useMilestonesQuery } from "@/features/taskboard/taskboard.queries";
import type { Milestone } from "@/features/taskboard/taskboard.types";
import {
  buildMilestoneColumns,
  buildMilestoneSummary,
  getMilestoneDateRangeLabel,
  getMilestoneStatusLabel,
} from "@/features/taskboard/taskboard.utils";
import { getErrorMessage } from "@/lib/api-error";

function MilestoneCard({ milestone }: { milestone: Milestone }) {
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
    </div>
  );
}

export function TaskboardPage() {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const currentTerm = useAppStore((state) => state.currentTerm);
  const currentUser = useAppStore((state) => state.currentUser);

  const milestonesQuery = useMilestonesQuery(isAuthenticated);
  const milestones = milestonesQuery.data?.items ?? [];
  const columns = buildMilestoneColumns(milestones);
  const summary = buildMilestoneSummary(milestones);

  return (
    <div className="page-stack">
      <PageSection className="hero-section">
        <p className="kicker">Task Progress</p>
        <h2 className="hero-title">毕业过程任务管理</h2>
        <p className="hero-copy">
          按待办、进行中和已完成三个状态维护毕业设计任务，结合截止时间和逾期标记持续跟踪开题、实现、论文与答辩准备进度。
        </p>
      </PageSection>

      <div className="grid-3">
        <div className="detail-card">
          <p style={{ fontWeight: 600 }}>总任务</p>
          <p className="muted small" style={{ marginTop: 10 }}>
            {summary.total} 项，来自当前用户的里程碑列表。
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
                    <MilestoneCard key={milestone.id} milestone={milestone} />
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
