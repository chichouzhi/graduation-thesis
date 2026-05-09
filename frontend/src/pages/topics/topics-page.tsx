import { useEffect, useState } from "react";

import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  useTopicQuery,
  useTopicsQuery,
} from "@/features/topics/topics.queries";
import type { Topic } from "@/features/topics/topics.types";
import {
  buildTopicAnalysis,
  buildTopicRecommendations,
  parseWorkbenchTerms,
  type StudentProfileDraft,
  type TopicAnalysisDraft,
  type TopicRecommendation,
} from "@/features/topics/topics-workbench";
import {
  buildTopicCapacityLabel,
  getTopicKeywordGroups,
  getTopicStatusLabel,
} from "@/features/topics/topics.utils";
import { getErrorMessage } from "@/lib/api-error";

type TopicsMode = "browse" | "teacher" | "student";

const initialTeacherDraft: TopicAnalysisDraft = {
  title: "",
  summary: "",
  requirements: "",
  keywords: "AI 助手，选题推荐，学生画像",
  capacity: "2",
};

const initialStudentDraft: StudentProfileDraft = {
  interests: "AI 学术助手，选题推荐",
  skills: "React，异步任务，接口联调",
  keywords: "画像，可解释推荐，工作台",
  goal: "希望选择一个适合答辩演示、又能体现大模型价值的题目",
  weeklyHours: "8",
};

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

function TopicTopicCard({
  topic,
  isSelected,
  onSelect,
}: {
  topic: Topic;
  isSelected: boolean;
  onSelect: (topicId: string) => void;
}) {
  return (
    <button
      type="button"
      className="topic-card"
      onClick={() => onSelect(topic.id)}
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
}

function AnalysisSummaryCard({
  analysis,
}: {
  analysis: ReturnType<typeof buildTopicAnalysis>;
}) {
  return (
    <>
      <div className="detail-card" style={{ marginTop: 22 }}>
        <p style={{ fontWeight: 600 }}>AI 分析摘要</p>
        <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
          {analysis.summary}
        </p>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>关键词与画像</p>
        <div className="keyword-row" style={{ marginTop: 12 }}>
          {analysis.focusKeywords.map((keyword) => (
            <span key={keyword} className="keyword-pill">
              {keyword}
            </span>
          ))}
        </div>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>难度判断</p>
        <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
          {analysis.difficultyLabel} · {analysis.difficultyReason}
        </p>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>所需能力</p>
        <div className="keyword-row" style={{ marginTop: 12 }}>
          {analysis.requiredCapabilities.map((item) => (
            <span key={item} className="keyword-pill">
              {item}
            </span>
          ))}
        </div>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>适合学生</p>
        <ul className="summary-points" style={{ marginTop: 12, paddingLeft: 0 }}>
          {analysis.suitableStudents.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>风险提示</p>
        <ul className="summary-points" style={{ marginTop: 12, paddingLeft: 0 }}>
          {analysis.risks.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>落地提醒</p>
        <ul className="summary-points" style={{ marginTop: 12, paddingLeft: 0 }}>
          {analysis.milestoneHints.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>答辩展示点</p>
        <ul className="summary-points" style={{ marginTop: 12, paddingLeft: 0 }}>
          {analysis.demoHighlights.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </>
  );
}

function RecommendationCard({
  item,
  active,
  onSelect,
}: {
  item: TopicRecommendation;
  active: boolean;
  onSelect: (topicId: string) => void;
}) {
  return (
    <button
      type="button"
      className="topic-card"
      onClick={() => onSelect(item.topic.id)}
      style={{
        width: "100%",
        cursor: "pointer",
        textAlign: "left",
        borderColor: active ? "rgba(31, 107, 104, 0.34)" : undefined,
        boxShadow: active ? "var(--shadow-subtle)" : "none",
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
          <h3 className="topic-title">{item.topic.title}</h3>
          <p className="muted small" style={{ marginTop: 10 }}>
            推荐分：{item.score}
          </p>
        </div>
        <span className="badge done">{item.matchedTerms.length} 个匹配词</span>
      </div>
      <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
        {item.topic.summary}
      </p>
      <div className="keyword-row">
        {item.matchedTerms.slice(0, 4).map((term) => (
          <span key={term} className="keyword-pill">
            {term}
          </span>
        ))}
      </div>
      {item.reasons.length ? (
        <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
          {item.reasons[0]}
        </p>
      ) : null}
      {item.warning ? (
        <p className="muted small" style={{ marginTop: 12 }}>
          {item.warning}
        </p>
      ) : null}
    </button>
  );
}

export function TopicsPage() {
  const [mode, setMode] = useState<TopicsMode>("browse");
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [teacherDraft, setTeacherDraft] = useState<TopicAnalysisDraft>(initialTeacherDraft);
  const [studentDraft, setStudentDraft] = useState<StudentProfileDraft>(initialStudentDraft);
  const [analysisResult, setAnalysisResult] = useState<ReturnType<typeof buildTopicAnalysis> | null>(
    null,
  );
  const [recommendationResult, setRecommendationResult] = useState<TopicRecommendation[]>([]);

  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const currentTerm = useAppStore((state) => state.currentTerm);

  const topicsQuery = useTopicsQuery(isAuthenticated, currentTerm.id);
  const detailQuery = useTopicQuery(selectedTopicId, Boolean(selectedTopicId));

  const topics = topicsQuery.data?.items ?? [];
  const portraitTopics = topics.filter((topic) => (topic.portrait?.keywords ?? []).length > 0);

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

  const selectedTopic = detailQuery.data?.id === selectedTopicId ? detailQuery.data : topics.find((topic) => topic.id === selectedTopicId) ?? null;
  const keywordGroups = selectedTopic
    ? getTopicKeywordGroups(selectedTopic)
    : { primary: [], derived: [] };
  const keywordJobStatusLabel = selectedTopic
    ? formatJobStatusLabel(selectedTopic.llmKeywordJobStatus)
    : "";

  const selectedRecommendation = recommendationResult.find((item) => item.topic.id === selectedTopicId) ?? null;

  function syncTeacherDraftFromTopic(topic: Topic) {
    setTeacherDraft({
      title: topic.title,
      summary: topic.summary,
      requirements: topic.requirements,
      keywords: [
        ...topic.techKeywords,
        ...(topic.portrait?.keywords ?? []),
      ].join("，"),
      capacity: String(topic.capacity),
    });
  }

  function handleAnalyzeTopic() {
    setAnalysisResult(buildTopicAnalysis(teacherDraft));
    setMode("teacher");
  }

  function handleRecommendTopics() {
    setRecommendationResult(buildTopicRecommendations(topics, studentDraft));
    setMode("student");
  }

  const currentTopicCount = topics.length;
  const keywordCoverage = portraitTopics.length;
  const recommendationCount = recommendationResult.length;

  return (
    <div className="page-stack">
      <PageSection className="hero-section">
        <p className="kicker">Topic Workbench</p>
        <h2 className="hero-title">题目分析与学生推荐</h2>
        <p className="hero-copy">
          老师先录入题目并生成结构化分析，学生再输入兴趣、技能和目标做推荐试算。当前页面先用前端演示逻辑落地这条闭环，后续可以直接切到真实大模型接口。
        </p>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 22 }}>
          <Button variant={mode === "browse" ? "default" : "outline"} onClick={() => setMode("browse")}>
            题目浏览
          </Button>
          <Button
            variant={mode === "teacher" ? "default" : "outline"}
            onClick={() => setMode("teacher")}
          >
            老师分析
          </Button>
          <Button
            variant={mode === "student" ? "default" : "outline"}
            onClick={() => setMode("student")}
          >
            学生推荐
          </Button>
        </div>
      </PageSection>

      <div className="grid-3">
        <div className="detail-card">
          <p style={{ fontWeight: 600 }}>当前学期题目</p>
          <p className="muted small" style={{ marginTop: 10 }}>
            {currentTopicCount} 条，支持浏览和分析导入。
          </p>
        </div>
        <div className="detail-card">
          <p style={{ fontWeight: 600 }}>已有画像题目</p>
          <p className="muted small" style={{ marginTop: 10 }}>
            {keywordCoverage} 条，适合用于教师分析和推荐解释。
          </p>
        </div>
        <div className="detail-card">
          <p style={{ fontWeight: 600 }}>推荐试算结果</p>
          <p className="muted small" style={{ marginTop: 10 }}>
            {recommendationCount} 条，当前仅在学生点击“开始推荐”后生成。
          </p>
        </div>
      </div>

      {mode === "browse" ? (
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
                {topics.map((topic) => (
                  <TopicTopicCard
                    key={topic.id}
                    topic={topic}
                    isSelected={topic.id === selectedTopicId}
                    onSelect={setSelectedTopicId}
                  />
                ))}
              </div>
            ) : (
              <div style={{ marginTop: 22 }}>
                <EmptyState title="暂无题目" description="当前学期还没有可浏览的课题数据。" />
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
                <EmptyState title="暂无题目详情" description="题目详情尚未返回，请稍后重试。" />
              </div>
            )}
          </PageSection>
        </div>
      ) : null}

      {mode === "teacher" ? (
        <div className="topics-layout">
          <PageSection className="paper">
            <SectionHeading
              title="老师输入题目"
              description="先把题目标题、摘要、要求和关键词整理成分析输入，再生成结构化画像。"
            />

            <div className="form-stack">
              <div className="field">
                <label htmlFor="teacher-title">题目名称</label>
                <Input
                  id="teacher-title"
                  value={teacherDraft.title}
                  onChange={(event) =>
                    setTeacherDraft((current) => ({ ...current, title: event.target.value }))
                  }
                  placeholder="例如：面向毕业设计场景的 AI 学术助手工作台"
                />
              </div>
              <div className="field">
                <label htmlFor="teacher-summary">题目摘要</label>
                <Textarea
                  id="teacher-summary"
                  value={teacherDraft.summary}
                  onChange={(event) =>
                    setTeacherDraft((current) => ({ ...current, summary: event.target.value }))
                  }
                  placeholder="简要描述题目要解决什么问题。"
                />
              </div>
              <div className="field">
                <label htmlFor="teacher-requirements">研究要求</label>
                <Textarea
                  id="teacher-requirements"
                  value={teacherDraft.requirements}
                  onChange={(event) =>
                    setTeacherDraft((current) => ({
                      ...current,
                      requirements: event.target.value,
                    }))
                  }
                  placeholder="例如：熟悉 React、Flask、异步任务队列与推荐逻辑。"
                />
              </div>
              <div className="field">
                <label htmlFor="teacher-keywords">题目关键词</label>
                <Input
                  id="teacher-keywords"
                  value={teacherDraft.keywords}
                  onChange={(event) =>
                    setTeacherDraft((current) => ({ ...current, keywords: event.target.value }))
                  }
                  placeholder="用逗号分隔，如：AI 助手，选题推荐，画像"
                />
              </div>
              <div className="field">
                <label htmlFor="teacher-capacity">容量</label>
                <Input
                  id="teacher-capacity"
                  value={teacherDraft.capacity}
                  onChange={(event) =>
                    setTeacherDraft((current) => ({ ...current, capacity: event.target.value }))
                  }
                  placeholder="例如：2"
                />
              </div>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 18 }}>
              <Button
                variant="outline"
                onClick={() => selectedTopic && syncTeacherDraftFromTopic(selectedTopic)}
                disabled={!selectedTopic}
              >
                导入当前选中题目
              </Button>
              <Button
                onClick={handleAnalyzeTopic}
                disabled={
                  !teacherDraft.title.trim() &&
                  !teacherDraft.summary.trim() &&
                  !teacherDraft.requirements.trim()
                }
              >
                生成分析摘要
              </Button>
            </div>

            <div style={{ marginTop: 24 }}>
              <SectionHeading
                title="题目参考"
                description="点击任意题目可快速导入到分析表单。"
              />

              {topicsQuery.isLoading ? (
                <div style={{ marginTop: 22 }}>
                  <EmptyState
                    title="正在加载题目列表"
                    description="系统正在同步当前学期的课题信息，请稍候。"
                  />
                </div>
              ) : topics.length ? (
                <div className="topic-list">
                  {topics.map((topic) => (
                    <TopicTopicCard
                      key={topic.id}
                      topic={topic}
                      isSelected={topic.id === selectedTopicId}
                      onSelect={(topicId) => {
                        setSelectedTopicId(topicId);
                        const current = topics.find((item) => item.id === topicId);
                        if (current) {
                          syncTeacherDraftFromTopic(current);
                        }
                      }}
                    />
                  ))}
                </div>
              ) : (
                <div style={{ marginTop: 22 }}>
                  <EmptyState title="暂无题目" description="没有可参考的课题数据。" />
                </div>
              )}
            </div>
          </PageSection>

          <PageSection className="paper">
            <SectionHeading
              title="AI 分析结果"
              description="这里展示题目画像、适合学生类型和实现风险，后续可以替换为真实大模型输出。"
            />

            {analysisResult ? (
              <AnalysisSummaryCard analysis={analysisResult} />
            ) : (
              <div style={{ marginTop: 22 }}>
                <EmptyState
                  title="等待生成分析"
                  description="填写题目信息后点击“生成分析摘要”，这里会出现结构化画像。"
                />
              </div>
            )}

            <div
              className="detail-card"
              style={{
                marginTop: 18,
                borderColor: "rgba(31, 107, 104, 0.18)",
                background: "rgba(223, 236, 235, 0.56)",
              }}
            >
              <p style={{ fontWeight: 600 }}>落地说明</p>
              <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                当前页面把“老师录题 - 题目分析 - 学生推荐”串成了完整前端演示流。等后端补上真实分析接口后，只需要把本页的本地分析函数替换成 API 调用即可。
              </p>
            </div>
          </PageSection>
        </div>
      ) : null}

      {mode === "student" ? (
        <div className="topics-layout">
          <PageSection className="paper">
            <SectionHeading
              title="学生画像输入"
              description="把兴趣、技能和目标整理成推荐输入，让系统先做一轮匹配试算。"
            />

            <div className="form-stack">
              <div className="field">
                <label htmlFor="student-interests">兴趣方向</label>
                <Textarea
                  id="student-interests"
                  value={studentDraft.interests}
                  onChange={(event) =>
                    setStudentDraft((current) => ({ ...current, interests: event.target.value }))
                  }
                  placeholder="例如：AI 学术助手、毕业设计、推荐系统"
                />
              </div>
              <div className="field">
                <label htmlFor="student-skills">已具备技能</label>
                <Textarea
                  id="student-skills"
                  value={studentDraft.skills}
                  onChange={(event) =>
                    setStudentDraft((current) => ({ ...current, skills: event.target.value }))
                  }
                  placeholder="例如：React、Flask、接口联调、论文写作"
                />
              </div>
              <div className="field">
                <label htmlFor="student-keywords">补充关键词</label>
                <Input
                  id="student-keywords"
                  value={studentDraft.keywords}
                  onChange={(event) =>
                    setStudentDraft((current) => ({ ...current, keywords: event.target.value }))
                  }
                  placeholder="例如：可解释推荐，画像，异步任务"
                />
              </div>
              <div className="field">
                <label htmlFor="student-goal">目标描述</label>
                <Textarea
                  id="student-goal"
                  value={studentDraft.goal}
                  onChange={(event) =>
                    setStudentDraft((current) => ({ ...current, goal: event.target.value }))
                  }
                  placeholder="例如：希望做一个能展示模型价值、适合答辩演示的题目。"
                />
              </div>
              <div className="field">
                <label htmlFor="student-hours">每周投入时间（小时）</label>
                <Input
                  id="student-hours"
                  value={studentDraft.weeklyHours}
                  onChange={(event) =>
                    setStudentDraft((current) => ({ ...current, weeklyHours: event.target.value }))
                  }
                  placeholder="例如：8"
                />
              </div>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 18 }}>
              <Button
                variant="outline"
                onClick={() =>
                  setStudentDraft({
                    interests: initialStudentDraft.interests,
                    skills: initialStudentDraft.skills,
                    keywords: initialStudentDraft.keywords,
                    goal: initialStudentDraft.goal,
                    weeklyHours: initialStudentDraft.weeklyHours,
                  })
                }
              >
                恢复示例输入
              </Button>
              <Button onClick={handleRecommendTopics}>开始推荐</Button>
            </div>

            <div
              className="detail-card"
              style={{
                marginTop: 18,
                borderColor: "rgba(15, 76, 117, 0.18)",
                background: "rgba(222, 239, 248, 0.55)",
              }}
            >
              <p style={{ fontWeight: 600 }}>推荐说明</p>
              <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                当前推荐试算优先匹配题目关键词、系统画像和容量信息，结果是前端演示版，后续可以直接接入真实 `/recommendations/topics` 或学生画像保存接口。
              </p>
            </div>
          </PageSection>

          <PageSection className="paper">
            <SectionHeading
              title="推荐结果"
              description="点击任意推荐项可以切换右侧题目详情。"
            />

            {!recommendationResult.length ? (
              <div style={{ marginTop: 22 }}>
                <EmptyState
                  title="等待生成推荐"
                  description="填写学生画像后点击“开始推荐”，这里会列出匹配的课题。"
                />
              </div>
            ) : (
              <div className="topic-list">
                {recommendationResult.map((item) => (
                  <RecommendationCard
                    key={item.topic.id}
                    item={item}
                    active={item.topic.id === selectedTopicId}
                    onSelect={setSelectedTopicId}
                  />
                ))}
              </div>
            )}

            {selectedRecommendation ? (
              <div className="detail-card" style={{ marginTop: 18 }}>
                <p style={{ fontWeight: 600 }}>当前选中的推荐题目</p>
                <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                  {selectedRecommendation.topic.title}
                </p>
                <p className="muted small" style={{ marginTop: 10, lineHeight: 1.9 }}>
                  {selectedRecommendation.topic.summary}
                </p>
                <div className="keyword-row">
                  {selectedRecommendation.topic.techKeywords.map((keyword) => (
                    <span key={keyword} className="keyword-pill">
                      {keyword}
                    </span>
                  ))}
                </div>
                <ul className="summary-points" style={{ marginTop: 12, paddingLeft: 0 }}>
                  {selectedRecommendation.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div
              className="detail-card"
              style={{
                marginTop: 18,
                borderColor: "rgba(31, 107, 104, 0.18)",
                background: "rgba(223, 236, 235, 0.56)",
              }}
            >
              <p style={{ fontWeight: 600 }}>当前匹配逻辑</p>
              <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                题目推荐先看“题目画像 + 学生输入画像”的交集，再结合容量和可解释性排序。输入里已经支持逗号分隔的关键词，便于后续直接替换成模型分析结果。
              </p>
              <p className="muted small" style={{ marginTop: 10, lineHeight: 1.9 }}>
                学生输入词条数：{parseWorkbenchTerms(studentDraft.interests).length +
                  parseWorkbenchTerms(studentDraft.skills).length +
                  parseWorkbenchTerms(studentDraft.keywords).length}
              </p>
            </div>
          </PageSection>
        </div>
      ) : null}
    </div>
  );
}
