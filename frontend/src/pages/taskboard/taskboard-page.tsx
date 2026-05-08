import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { taskColumns } from "@/features/taskboard/taskboard.mock";

export function TaskboardPage() {
  return (
    <div className="page-stack">
      <PageSection className="hero-section">
        <p className="kicker">Task Progress</p>
        <h2 className="hero-title">毕业过程任务管理</h2>
        <p className="hero-copy">
          按阶段维护开题调研、系统实现、论文撰写和验收准备任务，记录截止时间与优先级，持续跟踪毕业设计进度。
        </p>
      </PageSection>

      <PageSection className="paper">
        <SectionHeading title="毕业任务看板" description="查看各阶段任务数量、截止日期和优先级，后续可同步教师反馈与状态更新。" />
      </PageSection>

      <div className="task-column-list">
        {taskColumns.map((column) => (
          <section key={column.id} className="task-column">
            <div className="column-header">
              <h3>{column.title}</h3>
              <span className="priority-pill">{column.items.length} 项</span>
            </div>
            <div style={{ display: "grid", gap: 14, marginTop: 18 }}>
              {column.items.map((item) => (
                <div key={item.id} className="task-card">
                  <h4 className="task-title">{item.title}</h4>
                  <p className="muted small" style={{ marginTop: 10 }}>
                    截止时间：{item.due}
                  </p>
                  <p className="muted small" style={{ marginTop: 6 }}>
                    优先级：{item.priority}
                  </p>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
