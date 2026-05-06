import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { topics } from "@/features/topics/topics.mock";

export function TopicsPage() {
  return (
    <div className="topics-layout">
      <PageSection className="paper">
        <SectionHeading title="题目浏览" description="以选题辅助视角组织题目，而不是简单表格管理。" />
        <div className="topic-list">
          {topics.map((topic) => (
            <article key={topic.id} className="topic-card">
              <h3 className="topic-title">{topic.title}</h3>
              <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                {topic.summary}
              </p>
              <div className="keyword-row">
                {topic.keywords.map((keyword) => (
                  <span key={keyword} className="keyword-pill">
                    {keyword}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </PageSection>

      <PageSection className="paper">
        <SectionHeading title="题目详情摘要" description="预留后续详情查看与志愿状态展示区域。" />
        <div className="detail-card" style={{ marginTop: 22 }}>
          <h3>{topics[0].title}</h3>
          <p style={{ marginTop: 18, fontWeight: 600 }}>研究要求</p>
          <p className="muted small" style={{ marginTop: 10, lineHeight: 1.9 }}>
            {topics[0].requirements}
          </p>
          <p style={{ marginTop: 18, fontWeight: 600 }}>容量</p>
          <p className="muted small" style={{ marginTop: 10 }}>
            {topics[0].capacity} 人
          </p>
        </div>
      </PageSection>
    </div>
  );
}
