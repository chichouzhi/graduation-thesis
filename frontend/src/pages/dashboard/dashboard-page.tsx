import { ArrowRight, Bot, CheckCircle2, Clock3, Files } from "lucide-react";
import { Link } from "react-router-dom";

import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { studentWorkspace } from "@/data/student-workspace";
import {
  dashboardActivities,
  dashboardStats,
  dashboardStatusOverview,
  dashboardTimeline,
} from "@/features/dashboard/dashboard.mock";

const statIcons = [Bot, Files, Clock3, CheckCircle2];

export function DashboardPage() {
  return (
    <div className="page-stack">
      <PageSection className="hero-section">
        <p className="kicker">Current Focus</p>
        <h2 className="hero-title">{studentWorkspace.currentFocus}</h2>
        <p className="hero-copy">
          你正在围绕聊天分析、文档总结、选题整理和答辩准备推进毕业设计。这个首页优先展示最近工作、任务状态与下一步动作。
        </p>
      </PageSection>

      <div className="grid-4">
        {dashboardStats.map((stat, index) => {
          const Icon = statIcons[index];
          return <StatCard key={stat.id} label={stat.label} value={stat.value} hint={stat.hint} icon={<Icon size={20} />} />;
        })}
      </div>

      <div className="grid-2 wide">
        <PageSection className="paper">
          <SectionHeading title="近期工作" description="把近期最重要的推进事项集中在同一视图中。" />
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
        </PageSection>

        <PageSection className="paper">
          <SectionHeading title="异步任务状态总览" description="把聊天与文档处理的当前状态集中展示，方便答辩时讲清异步链路。" />
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
        </PageSection>
      </div>

      <div className="grid-2 wide">
        <PageSection className="paper">
          <SectionHeading title="快捷入口" description="从主页直接进入当前最常用的演示链路。" />
          <div className="quick-links">
            {studentWorkspace.quickLinks.map((item) => (
              <Link key={item.to} to={item.to} className="quick-link">
                <span>{item.label}</span>
                <ArrowRight size={16} />
              </Link>
            ))}
          </div>
        </PageSection>

        <PageSection className="paper">
          <SectionHeading title="工作台提示" description="让首页更像产品化工作区，而不只是统计卡片集合。" />
          <div className="detail-card" style={{ marginTop: 22 }}>
            <h3>当前学期建议</h3>
            <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
              先用 Chat 梳理答辩表述，再到 Documents 查看论文摘要结果，最后回到 Taskboard 检查剩余节点，会更适合完整演示“AI 学术助手工作台”的主线。
            </p>
          </div>
        </PageSection>
      </div>

      <PageSection className="paper">
        <SectionHeading title="最近活动" description="帮助答辩演示时快速讲清系统的近期状态变化。" />
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
      </PageSection>
    </div>
  );
}
