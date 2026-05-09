import { useEffect, useState } from "react";

import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateTopicMutation,
  useTopicQuery,
  useTopicRecommendationsQuery,
  useUpdateTopicMutation,
  useTopicsQuery,
} from "@/features/topics/topics.queries";
import type { RecommendationTopicItem, Topic } from "@/features/topics/topics.types";
import {
  buildStudentProfilePatch,
  mapStudentProfileToDraft,
  type StudentProfileDraft,
} from "@/pages/topics/topics-page.utils";
import {
  buildTopicCapacityLabel,
  getTopicKeywordGroups,
  getTopicStatusLabel,
} from "@/features/topics/topics.utils";
import {
  buildCreateTopicRequest,
  buildPatchTopicRequest,
  type TeacherTopicDraft,
} from "@/pages/topics/topics-page.utils";
import { useUpdateUserMeMutation, useUserMeQuery } from "@/features/users/users.queries";
import { getErrorMessage } from "@/lib/api-error";

type TopicsMode = "browse" | "teacher" | "student";

const initialTeacherDraft: TeacherTopicDraft = {
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
      return "题目画像待处理";
    case "running":
      return "题目画像分析中";
    case "done":
      return "题目画像已完成";
    case "failed":
      return "题目画像分析失败";
    default:
      return "";
  }
}

function formatDifficultyLabel(label?: "basic" | "intermediate" | "advanced" | null) {
  switch (label) {
    case "basic":
      return "基础";
    case "intermediate":
      return "进阶";
    case "advanced":
      return "挑战";
    default:
      return "未标注";
  }
}

function formatCapacityStatusLabel(status?: "available" | "nearly_full" | "full" | null) {
  switch (status) {
    case "available":
      return "容量充足";
    case "nearly_full":
      return "接近满员";
    case "full":
      return "已满员";
    default:
      return "容量未知";
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

function PortraitSummaryCard({
  topic,
}: {
  topic: Topic;
}) {
  const portrait = topic.portrait;

  if (!portrait) {
    return null;
  }

  return (
    <>
      <div className="detail-card" style={{ marginTop: 22 }}>
        <p style={{ fontWeight: 600 }}>AI 分析摘要</p>
        <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
          {portrait.summary ?? topic.summary}
        </p>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>关键词与画像</p>
        <div className="keyword-row" style={{ marginTop: 12 }}>
          {portrait.keywords.map((keyword) => (
            <span key={keyword} className="keyword-pill">
              {keyword}
            </span>
          ))}
        </div>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>难度判断</p>
        <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
          {formatDifficultyLabel(portrait.difficultyLabel)} · {portrait.difficultyReason ?? "暂无说明"}
        </p>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>所需能力</p>
        <div className="keyword-row" style={{ marginTop: 12 }}>
          {portrait.requiredCapabilities.map((item) => (
            <span key={item} className="keyword-pill">
              {item}
            </span>
          ))}
        </div>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>适合学生</p>
        <ul className="summary-points" style={{ marginTop: 12, paddingLeft: 0 }}>
          {portrait.suitableStudents.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="detail-card" style={{ marginTop: 18 }}>
        <p style={{ fontWeight: 600 }}>风险提示</p>
        <ul className="summary-points" style={{ marginTop: 12, paddingLeft: 0 }}>
          {portrait.risks.map((item) => (
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
  item: RecommendationTopicItem;
  active: boolean;
  onSelect: (topicId: string) => void;
}) {
  const explain = item.explain;

  return (
    <button
      type="button"
      className="topic-card"
      onClick={() => onSelect(item.topicId)}
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
          <h3 className="topic-title">{item.title}</h3>
          <p className="muted small" style={{ marginTop: 10 }}>
            推荐分：{item.score}
          </p>
        </div>
        <span className="badge done">{formatCapacityStatusLabel(explain?.capacityStatus)}</span>
      </div>
      <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
        {explain?.difficultyFit ?? "暂无难度匹配说明。"}
      </p>
      <div className="keyword-row">
        {(explain?.matchedCapabilities ?? []).slice(0, 4).map((term) => (
          <span key={term} className="keyword-pill">
            {term}
          </span>
        ))}
      </div>
      {explain?.reasons.length ? (
        <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
          {explain.reasons[0]}
        </p>
      ) : null}
      {explain?.warnings.length ? (
        <p className="muted small" style={{ marginTop: 12 }}>
          {explain.warnings[0]}
        </p>
      ) : null}
    </button>
  );
}

export function TopicsPage() {
  const [mode, setMode] = useState<TopicsMode>("browse");
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [teacherDraft, setTeacherDraft] = useState<TeacherTopicDraft>(initialTeacherDraft);
  const [studentDraft, setStudentDraft] = useState<StudentProfileDraft>(initialStudentDraft);
  const [studentDraftDirty, setStudentDraftDirty] = useState(false);
  const [recommendationEnabled, setRecommendationEnabled] = useState(false);

  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const currentTerm = useAppStore((state) => state.currentTerm);
  const currentUser = useAppStore((state) => state.currentUser);

  const topicsQuery = useTopicsQuery(isAuthenticated, currentTerm.id);
  const detailQuery = useTopicQuery(selectedTopicId, Boolean(selectedTopicId));
  const userMeQuery = useUserMeQuery(isAuthenticated && mode === "student");
  const createTopicMutation = useCreateTopicMutation();
  const updateTopicMutation = useUpdateTopicMutation();
  const updateUserMeMutation = useUpdateUserMeMutation();
  const recommendationsQuery = useTopicRecommendationsQuery(
    currentTerm.id,
    isAuthenticated && mode === "student" && recommendationEnabled,
  );

  const topics = topicsQuery.data?.items ?? [];
  const portraitTopics = topics.filter((topic) => (topic.portrait?.keywords ?? []).length > 0);
  const effectiveSelectedTopicId =
    selectedTopicId && topics.some((topic) => topic.id === selectedTopicId)
      ? selectedTopicId
      : topics[0]?.id ?? null;

  const selectedTopic =
    detailQuery.data?.id === effectiveSelectedTopicId
      ? detailQuery.data
      : topics.find((topic) => topic.id === effectiveSelectedTopicId) ?? null;
  const keywordGroups = selectedTopic
    ? getTopicKeywordGroups(selectedTopic)
    : { primary: [], derived: [] };
  const keywordJobStatusLabel = selectedTopic
    ? formatJobStatusLabel(selectedTopic.llmKeywordJobStatus)
    : "";
  const recommendationItems = recommendationsQuery.data?.items ?? [];
  const selectedRecommendation =
    recommendationItems.find((item) => item.topicId === effectiveSelectedTopicId) ?? null;

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

  useEffect(() => {
    if (mode !== "student" || studentDraftDirty) {
      return;
    }

    if (userMeQuery.data?.studentProfile) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStudentDraft(mapStudentProfileToDraft(userMeQuery.data.studentProfile));
    }
  }, [mode, studentDraftDirty, userMeQuery.data?.studentProfile]);

  async function handleSaveTeacherDraft() {
    if (!currentUser || !selectedTopic) {
      return;
    }

    const payload = buildPatchTopicRequest(teacherDraft);

    const savedTopic =
      selectedTopic.teacherId === currentUser.id && selectedTopic.status !== "published"
        ? await updateTopicMutation.mutateAsync({
            topicId: selectedTopic.id,
            payload,
          })
        : await createTopicMutation.mutateAsync(
            buildCreateTopicRequest(teacherDraft, currentTerm.id),
          );

    setSelectedTopicId(savedTopic.id);
    syncTeacherDraftFromTopic(savedTopic);
    await topicsQuery.refetch();
  }

  async function handleSaveAndRecommend() {
    await updateUserMeMutation.mutateAsync(buildStudentProfilePatch(studentDraft));
    setStudentDraftDirty(false);
    setRecommendationEnabled(true);
    await recommendationsQuery.refetch();
  }

  const currentTopicCount = topics.length;
  const keywordCoverage = portraitTopics.length;
  const recommendationCount = recommendationsQuery.data?.items.length ?? 0;

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
                    isSelected={topic.id === effectiveSelectedTopicId}
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
            {!effectiveSelectedTopicId ? (
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
                onClick={() => void handleSaveTeacherDraft()}
                disabled={
                  createTopicMutation.isPending ||
                  updateTopicMutation.isPending ||
                  !teacherDraft.title.trim() &&
                  !teacherDraft.summary.trim() &&
                  !teacherDraft.requirements.trim()
                }
              >
                保存并生成分析
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
                      isSelected={topic.id === effectiveSelectedTopicId}
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
              title="题目画像结果"
              description="这里展示后端返回的题目画像、适合学生类型和实现风险。"
            />

            {selectedTopic?.portrait ? (
              <PortraitSummaryCard topic={selectedTopic} />
            ) : (
              <div style={{ marginTop: 22 }}>
                <EmptyState
                  title="等待题目画像"
                  description="保存题目后，这里会展示后端异步生成的结构化画像。"
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
                当前页面把“老师录题 - 题目画像 - 学生推荐”串成了完整前端演示流。老师分析已切到后端题目画像字段，后续只需要继续补学生画像保存和推荐联调。
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
                  onChange={(event) => {
                    setStudentDraftDirty(true);
                    setStudentDraft((current) => ({ ...current, interests: event.target.value }));
                  }}
                  placeholder="例如：AI 学术助手、毕业设计、推荐系统"
                />
              </div>
              <div className="field">
                <label htmlFor="student-skills">已具备技能</label>
                <Textarea
                  id="student-skills"
                  value={studentDraft.skills}
                  onChange={(event) => {
                    setStudentDraftDirty(true);
                    setStudentDraft((current) => ({ ...current, skills: event.target.value }));
                  }}
                  placeholder="例如：React、Flask、接口联调、论文写作"
                />
              </div>
              <div className="field">
                <label htmlFor="student-keywords">补充关键词</label>
                <Input
                  id="student-keywords"
                  value={studentDraft.keywords}
                  onChange={(event) => {
                    setStudentDraftDirty(true);
                    setStudentDraft((current) => ({ ...current, keywords: event.target.value }));
                  }}
                  placeholder="例如：可解释推荐，画像，异步任务"
                />
              </div>
              <div className="field">
                <label htmlFor="student-goal">目标描述</label>
                <Textarea
                  id="student-goal"
                  value={studentDraft.goal}
                  onChange={(event) => {
                    setStudentDraftDirty(true);
                    setStudentDraft((current) => ({ ...current, goal: event.target.value }));
                  }}
                  placeholder="例如：希望做一个能展示模型价值、适合答辩演示的题目。"
                />
              </div>
              <div className="field">
                <label htmlFor="student-hours">每周投入时间（小时）</label>
                <Input
                  id="student-hours"
                  value={studentDraft.weeklyHours}
                  onChange={(event) => {
                    setStudentDraftDirty(true);
                    setStudentDraft((current) => ({ ...current, weeklyHours: event.target.value }));
                  }}
                  placeholder="例如：8"
                />
              </div>
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 18 }}>
              <Button
                variant="outline"
                onClick={() => {
                  setStudentDraft({
                    interests: initialStudentDraft.interests,
                    skills: initialStudentDraft.skills,
                    keywords: initialStudentDraft.keywords,
                    goal: initialStudentDraft.goal,
                    weeklyHours: initialStudentDraft.weeklyHours,
                  });
                  setStudentDraftDirty(true);
                }}
              >
                恢复示例输入
              </Button>
              <Button onClick={() => void handleSaveAndRecommend()}>
                保存画像并开始推荐
              </Button>
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
                当前推荐通过先保存学生画像，再调用后端的 `/recommendations/topics` 获取结果。后续只需要把这块换成真实联调数据即可。
              </p>
            </div>
          </PageSection>

          <PageSection className="paper">
            <SectionHeading
              title="推荐结果"
              description="点击任意推荐项可以切换右侧题目详情。"
            />

            {!recommendationEnabled ? (
              <div style={{ marginTop: 22 }}>
                <EmptyState
                  title="等待开始推荐"
                  description="先保存学生画像，系统再请求后端生成匹配结果。"
                />
              </div>
            ) : recommendationsQuery.isLoading ? (
              <div style={{ marginTop: 22 }}>
                <EmptyState
                  title="推荐生成中"
                  description="后端正在基于学生画像和当前学期题目计算推荐结果。"
                />
              </div>
            ) : recommendationsQuery.isError ? (
              <div style={{ marginTop: 22 }}>
                <EmptyState
                  title="推荐结果加载失败"
                  description={getErrorMessage(recommendationsQuery.error, "暂时无法获取推荐结果。")}
                  action={
                    <Button variant="outline" onClick={() => void recommendationsQuery.refetch()}>
                      重试
                    </Button>
                  }
                />
              </div>
            ) : !recommendationItems.length ? (
              <div style={{ marginTop: 22 }}>
                <EmptyState
                  title="暂无推荐结果"
                  description="当前学生画像和学期题目没有匹配到合适结果。"
                />
              </div>
            ) : (
              <div className="topic-list">
                {recommendationItems.map((item) => (
                  <RecommendationCard
                    key={item.topicId}
                    item={item}
                    active={item.topicId === effectiveSelectedTopicId}
                    onSelect={setSelectedTopicId}
                  />
                ))}
              </div>
            )}

            {selectedRecommendation ? (
              <div className="detail-card" style={{ marginTop: 18 }}>
                <p style={{ fontWeight: 600 }}>当前选中的推荐题目</p>
                <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                  {selectedRecommendation.title}
                </p>
                <p className="muted small" style={{ marginTop: 10, lineHeight: 1.9 }}>
                  推荐分：{selectedRecommendation.score} · {formatCapacityStatusLabel(selectedRecommendation.explain?.capacityStatus)}
                </p>
                <ul className="summary-points" style={{ marginTop: 12, paddingLeft: 0 }}>
                  {(selectedRecommendation.explain?.reasons ?? []).map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
                {selectedTopic ? (
                  <p className="muted small" style={{ marginTop: 10, lineHeight: 1.9 }}>
                    题目简介：{selectedTopic.summary}
                  </p>
                ) : null}
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
                推荐结果由后端返回的可解释字段驱动，前端只负责展示“匹配技能、关键词、容量状态、建议与风险”。学生画像输入已经预留了后续接模型分析结果的空间。
              </p>
            </div>
          </PageSection>
        </div>
      ) : null}
    </div>
  );
}
