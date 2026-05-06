import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { taskColumns } from "@/features/taskboard/taskboard.mock";

export function TaskboardPage() {
  return (
    <div className="page-stack">
      <PageSection className="paper">
        <SectionHeading title="毕业任务看板" description="以阶段推进的方式展示从开题到答辩准备的整体节奏。" />
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
