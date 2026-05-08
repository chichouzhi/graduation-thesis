import { useEffect, useMemo, useState } from "react";

import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import {
  useTopicQuery,
  useTopicsQuery,
} from "@/features/topics/topics.queries";
import {
  buildTopicCapacityLabel,
  getTopicKeywordGroups,
  getTopicStatusLabel,
} from "@/features/topics/topics.utils";
import { getErrorMessage } from "@/lib/api-error";

function formatJobStatusLabel(status?: "pending" | "running" | "done" | "failed" | null) {
  switch (status) {
    case "pending":
      return "关键词抽取待处理";
    case "running":
      return "关键词抽取进行中";
    case "done":
      return "关键词抽取已完成";
    case "failed":
      return "关键词抽取失败";
    default:
      return "";
  }
}

export function TopicsPage() {
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);

  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const currentTerm = useAppStore((state) => state.currentTerm);

  const topicsQuery = useTopicsQuery(isAuthenticated, currentTerm.id);
  const detailQuery = useTopicQuery(selectedTopicId, Boolean(selectedTopicId));

  const topics = useMemo(() => topicsQuery.data?.items ?? [], [topicsQuery.data?.items]);

  useEffect(() => {
    if (!topics.length) {
      if (selectedTopicId !== null) {
        setSelectedTopicId(null);
      }
      return;
    }

    if (selectedTopicId && topics.some((topic) => topic.id === selectedTopicId)) {
      return;
    }

    setSelectedTopicId(topics[0].id);
  }, [selectedTopicId, topics]);

  const selectedTopic = detailQuery.data?.id === selectedTopicId ? detailQuery.data : null;
  const keywordGroups = selectedTopic
    ? getTopicKeywordGroups(selectedTopic)
    : { primary: [], derived: [] };
  const keywordJobStatusLabel = selectedTopic
    ? formatJobStatusLabel(selectedTopic.llmKeywordJobStatus)
    : "";

  return (
    <div className="page-stack">
      <PageSection className="hero-section">
        <p className="kicker">Topic Discovery</p>
        <h2 className="hero-title">选题辅助浏览</h2>
        <p className="hero-copy">
          浏览当前学期已发布课题，查看研究摘要、能力要求、技术关键词和剩余容量，结合个人方向完成志愿选择。
        </p>
      </PageSection>

      <div className="topics-layout">
        <PageSection className="paper">
          <SectionHeading
            title="题目浏览"
            description={`当前学期：${currentTerm.name} · 按题目状态、容量和技术关键词查看可选课题。`}
          />
          {topicsQuery.isLoading ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="正在加载题目列表"
                description="系统正在同步当前学期的课题信息，请稍候。"
              />
            </div>
          ) : topicsQuery.isError ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="题目列表加载失败"
                description={getErrorMessage(topicsQuery.error, "暂时无法获取题目列表。")}
                action={
                  <Button variant="outline" onClick={() => topicsQuery.refetch()}>
                    重试
                  </Button>
                }
              />
            </div>
          ) : topics.length ? (
            <div className="topic-list">
              {topics.map((topic) => {
                const isSelected = topic.id === selectedTopicId;

                return (
                  <button
                    key={topic.id}
                    type="button"
                    className="topic-card"
                    onClick={() => setSelectedTopicId(topic.id)}
                    style={{
                      width: "100%",
                      cursor: "pointer",
                      textAlign: "left",
                      borderColor: isSelected ? "rgba(31, 107, 104, 0.34)" : undefined,
                      boxShadow: isSelected ? "var(--shadow-subtle)" : "none",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 12,
                        alignItems: "flex-start",
                      }}
                    >
                      <div>
                        <h3 className="topic-title">{topic.title}</h3>
                        <p className="muted small" style={{ marginTop: 10 }}>
                          {buildTopicCapacityLabel(topic)}
                        </p>
                      </div>
                      <span className="badge">{getTopicStatusLabel(topic.status)}</span>
                    </div>
                    <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                      {topic.summary}
                    </p>
                    <div className="keyword-row">
                      {topic.techKeywords.map((keyword) => (
                        <span key={keyword} className="keyword-pill">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="暂无题目"
                description="当前学期还没有可浏览的课题数据。"
              />
            </div>
          )}
        </PageSection>

        <PageSection className="paper">
          <SectionHeading
            title="题目详情摘要"
            description="右侧展示研究要求、关键词与容量信息，便于学生判断课题匹配度。"
          />
          {!selectedTopicId ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="尚未选择题目"
                description="从左侧选择一个题目后，这里会显示完整的研究摘要与要求。"
              />
            </div>
          ) : detailQuery.isLoading && !selectedTopic ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="正在同步题目详情"
                description="系统正在获取该题目的完整信息，请稍候。"
              />
            </div>
          ) : detailQuery.isError && !selectedTopic ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="题目详情加载失败"
                description={getErrorMessage(detailQuery.error, "暂时无法获取题目详情。")}
                action={
                  <Button variant="outline" onClick={() => detailQuery.refetch()}>
                    重试
                  </Button>
                }
              />
            </div>
          ) : selectedTopic ? (
            <>
              <div
                className="detail-card"
                style={{
                  marginTop: 22,
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  alignItems: "flex-start",
                }}
              >
                <div>
                  <h3>{selectedTopic.title}</h3>
                  <p className="muted small" style={{ marginTop: 10 }}>
                    学期：{currentTerm.name}
                  </p>
                </div>
                <span className="badge">{getTopicStatusLabel(selectedTopic.status)}</span>
              </div>

              <div className="detail-card" style={{ marginTop: 18 }}>
                <p style={{ fontWeight: 600 }}>题目摘要</p>
                <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                  {selectedTopic.summary}
                </p>
              </div>

              <div className="detail-card" style={{ marginTop: 18 }}>
                <p style={{ fontWeight: 600 }}>研究要求</p>
                <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                  {selectedTopic.requirements}
                </p>
              </div>

              <div className="detail-card" style={{ marginTop: 18 }}>
                <p style={{ fontWeight: 600 }}>技术关键词</p>
                {keywordGroups.primary.length ? (
                  <div className="keyword-row" style={{ marginTop: 12 }}>
                    {keywordGroups.primary.map((keyword) => (
                      <span key={keyword} className="keyword-pill">
                        {keyword}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="muted small" style={{ marginTop: 12 }}>
                    暂无技术关键词。
                  </p>
                )}
              </div>

              {keywordGroups.derived.length ? (
                <div className="detail-card" style={{ marginTop: 18 }}>
                  <p style={{ fontWeight: 600 }}>系统抽取关键词</p>
                  <div className="keyword-row" style={{ marginTop: 12 }}>
                    {keywordGroups.derived.map((keyword) => (
                      <span key={keyword} className="keyword-pill">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="detail-card" style={{ marginTop: 18 }}>
                <p style={{ fontWeight: 600 }}>容量与基础信息</p>
                <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                  容量：{buildTopicCapacityLabel(selectedTopic)}
                </p>
                <p className="muted small" style={{ marginTop: 8, lineHeight: 1.9 }}>
                  教师 ID：{selectedTopic.teacherId}
                </p>
                <p className="muted small" style={{ marginTop: 8, lineHeight: 1.9 }}>
                  学期 ID：{selectedTopic.termId}
                </p>
                <p className="muted small" style={{ marginTop: 8, lineHeight: 1.9 }}>
                  更新时间：{selectedTopic.updatedAt}
                </p>
              </div>

              {keywordJobStatusLabel ? (
                <div
                  className="detail-card"
                  style={{
                    marginTop: 18,
                    borderColor: "rgba(15, 76, 117, 0.18)",
                    background: "rgba(222, 239, 248, 0.55)",
                  }}
                >
                  <h3>关键词抽取状态</h3>
                  <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                    {keywordJobStatusLabel}
                  </p>
                </div>
              ) : null}
            </>
          ) : (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="暂无题目详情"
                description="题目详情尚未返回，请稍后重试。"
              />
            </div>
          )}
        </PageSection>
      </div>
    </div>
  );
}
