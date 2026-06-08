import { Bot, CheckCircle2, Clock3, Files } from "lucide-react";

import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { useConversationsQuery } from "@/features/chat/chat.queries";
import { useDocumentTasksQuery } from "@/features/documents/documents.queries";
import { useMilestonesQuery } from "@/features/taskboard/taskboard.queries";
import { useTopicsQuery } from "@/features/topics/topics.queries";
import {
  buildDashboardFocus,
  buildDashboardStatusOverview,
  buildDashboardStats,
  buildDashboardTimeline,
} from "@/pages/dashboard/dashboard-page.utils";

const statIcons = [Bot, Files, Clock3, CheckCircle2];

export function DashboardPage() {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const currentTerm = useAppStore((state) => state.currentTerm);
  const currentUser = useAppStore((state) => state.currentUser);

  const conversationsQuery = useConversationsQuery(isAuthenticated);
  const topicsQuery = useTopicsQuery(isAuthenticated, currentTerm.id);
  const documentTasksQuery = useDocumentTasksQuery(isAuthenticated);
  const milestonesQuery = useMilestonesQuery(isAuthenticated);

  const dashboardSnapshot = {
    conversations: conversationsQuery.data?.items ?? [],
    documentTasks: documentTasksQuery.data?.items ?? [],
    milestones: milestonesQuery.data?.items ?? [],
    topics: topicsQuery.data?.items ?? [],
  };

  const dashboardStats = buildDashboardStats(dashboardSnapshot);
  const dashboardTimeline = buildDashboardTimeline(dashboardSnapshot);
  const dashboardStatusOverview = buildDashboardStatusOverview(dashboardSnapshot);
  const focusMessage = buildDashboardFocus(dashboardSnapshot);

  const hasAnyData =
    dashboardSnapshot.conversations.length > 0 ||
    dashboardSnapshot.documentTasks.length > 0 ||
    dashboardSnapshot.milestones.length > 0 ||
    dashboardSnapshot.topics.length > 0;

  const hasAnyLoading =
    conversationsQuery.isLoading ||
    topicsQuery.isLoading ||
    documentTasksQuery.isLoading ||
    milestonesQuery.isLoading;

  const hasAnyError =
    conversationsQuery.isError ||
    topicsQuery.isError ||
    documentTasksQuery.isError ||
    milestonesQuery.isError;

  return (
    <div className="page-stack">
      <PageSection className="hero-section">
        <p className="kicker">Current Focus</p>
        <h2 className="hero-title">毕业设计选题支持系统工作台</h2>
        <p className="hero-copy">
          欢迎，{currentUser?.display_name ?? currentUser?.username ?? "同学"}。当前学期 {currentTerm.name} 已接入题目、文档、任务和会话数据，首页优先展示最近工作和任务状态。
        </p>

        <div
          className="detail-card"
          style={{
            marginTop: 18,
            borderColor: "rgba(31, 107, 104, 0.18)",
            background: "rgba(223, 236, 235, 0.56)",
          }}
        >
          <p style={{ fontWeight: 600 }}>当前重点</p>
          <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
            {focusMessage}
          </p>
        </div>
      </PageSection>

      <div className="grid-4">
        {dashboardStats.map((stat, index) => {
          const Icon = statIcons[index];
          return <StatCard key={stat.id} label={stat.label} value={stat.value} hint={stat.hint} icon={<Icon size={20} />} />;
        })}
      </div>

      <div className="grid-2 wide">
        <PageSection className="paper">
          <SectionHeading title="近期工作" description="把选题、文档和阶段任务中最靠近当前的动作集中在一起。" />

          {!hasAnyData && hasAnyLoading ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState title="正在加载近期工作" description="系统正在汇总题目、文档和里程碑信息，请稍候。" />
            </div>
          ) : !hasAnyData && hasAnyError ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState title="近期工作加载失败" description="首页概览暂时无法同步，请稍后重试。" />
            </div>
          ) : dashboardTimeline.length ? (
            <div className="timeline-list">
              {dashboardTimeline.map((item) => (
                <div key={item.id} className="timeline-item">
                  <div>
                    <h3>{item.title}</h3>
                    <p className="muted small" style={{ marginTop: 10 }}>
                      {item.detail}
                    </p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
              ))}
            </div>
          ) : (
            <div style={{ marginTop: 22 }}>
              <EmptyState title="暂无近期工作" description="当前没有可展示的近期任务节点。" />
            </div>
          )}
        </PageSection>

        <PageSection className="paper">
          <SectionHeading title="异步任务状态总览" description="查看题目画像、文档处理和阶段节点的整体进度。" />

          {!hasAnyData && hasAnyLoading ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState title="正在同步状态" description="系统正在读取任务和分析状态，请稍候。" />
            </div>
          ) : !hasAnyData && hasAnyError ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState title="状态总览加载失败" description="暂时无法获取工作台状态。" />
            </div>
          ) : (
            <div className="timeline-list">
              {dashboardStatusOverview.map((item) => (
                <div key={item.id} className="timeline-item">
                  <div>
                    <h3>{item.label}</h3>
                    <p className="muted small" style={{ marginTop: 10 }}>
                      {item.detail}
                    </p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
              ))}
            </div>
          )}
        </PageSection>
      </div>
    </div>
  );
}
