import { Upload } from "lucide-react";

import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { documentDetail, documentTasks } from "@/features/documents/documents.mock";

export function DocumentsPage() {
  return (
    <div className="page-stack">
      <PageSection className="paper" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <p className="kicker">Document Pipeline</p>
          <h2 style={{ marginTop: 14, fontSize: 30, letterSpacing: "-0.04em" }}>PDF 分析与总结任务</h2>
          <p className="muted small" style={{ marginTop: 10, lineHeight: 1.9 }}>
            本轮只展示静态骨架，但页面结构已经为上传受理、任务推进与结果回写预留位置。
          </p>
        </div>
        <div>
          <Button>
            <Upload size={16} />
            上传 PDF
          </Button>
        </div>
      </PageSection>

      <div className="documents-layout">
        <PageSection className="paper">
          <SectionHeading title="任务列表" description="左侧保留后续轮询驱动的任务概览区。" />
          <div className="document-list">
            {documentTasks.map((task) => (
              <div key={task.id} className="document-item">
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
                  <div>
                    <h3>{task.filename}</h3>
                    <p className="muted small" style={{ marginTop: 10 }}>
                      {task.currentStage}
                    </p>
                  </div>
                  <StatusBadge status={task.status} />
                </div>
                <p className="muted small" style={{ marginTop: 12 }}>
                  {task.progress}
                </p>
              </div>
            ))}
          </div>
        </PageSection>

        <PageSection className="paper">
          <SectionHeading title="任务详情" description="右侧详情区承接阶段状态、摘要结果与失败反馈。" />
          <div className="detail-card" style={{ marginTop: 22, display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
            <div>
              <h3>{documentDetail.filename}</h3>
              <p className="muted small" style={{ marginTop: 10 }}>
                task_type: {documentDetail.taskType} · language: {documentDetail.language}
              </p>
            </div>
            <StatusBadge status={documentDetail.status} />
          </div>

          <div className="detail-stages">
            {documentDetail.stages.map((stage) => (
              <div key={stage.label} className="detail-card">
                <p style={{ fontWeight: 600 }}>{stage.label}</p>
                <div style={{ marginTop: 12 }}>
                  <StatusBadge status={stage.value} />
                </div>
              </div>
            ))}
          </div>

          <div className="detail-card" style={{ marginTop: 18, background: "rgba(255,255,255,0.92)" }}>
            <h3>摘要结果</h3>
            <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
              {documentDetail.summary}
            </p>
            <ul className="summary-points">
              {documentDetail.bulletPoints.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </div>
        </PageSection>
      </div>
    </div>
  );
}
