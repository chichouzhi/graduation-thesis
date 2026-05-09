import { ArrowRight, Bot, CheckCircle2, Clock3, Files } from "lucide-react";
import { Link } from "react-router-dom";

import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { useConversationsQuery } from "@/features/chat/chat.queries";
import { useDocumentTasksQuery } from "@/features/documents/documents.queries";
import { useAssignmentsQuery } from "@/features/selection/selection.queries";
import { useMilestonesQuery } from "@/features/taskboard/taskboard.queries";
import { useTopicsQuery } from "@/features/topics/topics.queries";
import {
  buildDashboardActivities,
  buildDashboardFocus,
  buildDashboardStatusOverview,
  buildDashboardStats,
  buildDashboardTimeline,
} from "@/pages/dashboard/dashboard-page.utils";

const quickLinks = [
  { label: "继续选题咨询", to: "/app/chat" },
  { label: "查看文献摘要", to: "/app/documents" },
  { label: "浏览可选课题", to: "/app/topics" },
  { label: "更新阶段任务", to: "/app/taskboard" },
];

const statIcons = [Bot, Files, Clock3, CheckCircle2];

function formatAssignmentStatusLabel(status: string) {
  switch (status) {
    case "active":
      return "已确认指导";
    case "cancelled":
      return "已取消";
    default:
      return status;
  }
}

export function DashboardPage() {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const currentTerm = useAppStore((state) => state.currentTerm);
  const currentUser = useAppStore((state) => state.currentUser);

  const conversationsQuery = useConversationsQuery(isAuthenticated);
  const topicsQuery = useTopicsQuery(isAuthenticated, currentTerm.id);
  const documentTasksQuery = useDocumentTasksQuery(isAuthenticated);
  const milestonesQuery = useMilestonesQuery(isAuthenticated);
  const assignmentsQuery = useAssignmentsQuery(isAuthenticated);
  const assignments = assignmentsQuery.data?.items ?? [];

  const dashboardSnapshot = {
    conversations: conversationsQuery.data?.items ?? [],
    documentTasks: documentTasksQuery.data?.items ?? [],
    milestones: milestonesQuery.data?.items ?? [],
    topics: topicsQuery.data?.items ?? [],
  };

  const dashboardStats = buildDashboardStats(dashboardSnapshot);
  const dashboardTimeline = buildDashboardTimeline(dashboardSnapshot);
  const dashboardActivities = buildDashboardActivities(dashboardSnapshot);
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
        <h2 className="hero-title">AI 学术助手工作台</h2>
        <p className="hero-copy">
          欢迎，{currentUser?.display_name ?? currentUser?.username ?? "同学"}。当前学期 {currentTerm.name} 已接入题目、文档、任务和会话数据，首页优先展示最近工作、任务状态和最近活动。
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

      <div className="grid-2 wide">
        <PageSection className="paper">
          <SectionHeading title="快捷入口" description="从主页直接进入当前最常用的学习与研发链路。" />
          <div className="quick-links">
            {quickLinks.map((item) => (
              <Link key={item.to} to={item.to} className="quick-link">
                <span>{item.label}</span>
                <ArrowRight size={16} />
              </Link>
            ))}
          </div>
        </PageSection>

        <PageSection className="paper">
          <SectionHeading title="指导关系" description="展示老师接受志愿后形成的师生课题绑定。" />

          {assignmentsQuery.isLoading ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState title="正在加载指导关系" description="系统正在同步已确认的选题关系。" />
            </div>
          ) : assignmentsQuery.isError ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState title="指导关系加载失败" description="暂时无法获取师生指导关系。" />
            </div>
          ) : assignments.length ? (
            <div className="timeline-list">
              {assignments.slice(0, 3).map((assignment) => (
                <div key={assignment.id} className="timeline-item">
                  <div>
                    <h3>{assignment.topicTitle ?? assignment.topicId}</h3>
                    <p className="muted small" style={{ marginTop: 10 }}>
                      {assignment.studentName ?? assignment.studentId} ·{" "}
                      {formatAssignmentStatusLabel(assignment.status)}
                    </p>
                    <p className="muted small" style={{ marginTop: 8 }}>
                      确认时间：{assignment.confirmedAt ?? "待后端返回"}
                    </p>
                  </div>
                  <StatusBadge
                    status={assignment.status === "active" ? "done" : "failed"}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="暂无指导关系"
                description="老师接受学生志愿后，这里会展示正式的师生课题关系。"
              />
            </div>
          )}
        </PageSection>
      </div>

      <PageSection className="paper">
        <SectionHeading title="下一步建议" description="根据当前学期进度整理常用操作，帮助保持节奏。" />
        <div className="detail-card" style={{ marginTop: 22 }}>
          <h3>当前学期建议</h3>
          <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
            {dashboardStatusOverview.some((item) => item.status === "running")
              ? "先看 Topics 和 Documents 的异步结果，再回到 Taskboard 补齐进行中的节点。"
              : "可以先用 Chat 梳理下一个选题问题，再到 Topics 和 Taskboard 继续推进。"}
          </p>
        </div>
      </PageSection>

      <PageSection className="paper">
        <SectionHeading title="最近活动" description="记录本学期工作区中的关键状态变化。" />

        {!hasAnyData && hasAnyLoading ? (
          <div style={{ marginTop: 22 }}>
            <EmptyState title="正在加载最近活动" description="系统正在整理最新变更，请稍候。" />
          </div>
        ) : !hasAnyData && hasAnyError ? (
          <div style={{ marginTop: 22 }}>
            <EmptyState title="最近活动加载失败" description="暂时无法获取活动流。" />
          </div>
        ) : dashboardActivities.length ? (
          <div className="activity-grid">
            {dashboardActivities.map((item) => (
              <article key={item.id} className="activity-card">
                <div className="activity-time">{item.time}</div>
                <h3 className="activity-title">{item.title}</h3>
                <p className="muted small" style={{ marginTop: 10 }}>
                  {item.description}
                </p>
              </article>
            ))}
          </div>
        ) : (
          <div style={{ marginTop: 22 }}>
            <EmptyState title="暂无最近活动" description="当前没有可以展示的最新更新。" />
          </div>
        )}
      </PageSection>
    </div>
  );
}
