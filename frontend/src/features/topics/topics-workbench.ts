import type { Topic } from "@/features/topics/topics.types";

const termSplitPattern = /[\n,，、;；/|]+/;

export type TopicAnalysisDraft = {
  title: string;
  summary: string;
  requirements: string;
  keywords: string;
  capacity: string;
};

export type TopicAnalysisResult = {
  focusKeywords: string[];
  difficultyLabel: "基础" | "进阶" | "挑战";
  difficultyReason: string;
  requiredCapabilities: string[];
  suitableStudents: string[];
  risks: string[];
  milestoneHints: string[];
  demoHighlights: string[];
  summary: string;
};

export type StudentProfileDraft = {
  interests: string;
  skills: string;
  keywords: string;
  goal: string;
  weeklyHours: string;
};

export type TopicRecommendation = {
  topic: Topic;
  score: number;
  matchedTerms: string[];
  reasons: string[];
  warning: string | null;
};

function normalizeTerm(text: string) {
  return text.trim().toLowerCase();
}

export function parseWorkbenchTerms(text: string) {
  const seen = new Map<string, string>();
  for (const chunk of text.split(termSplitPattern)) {
    const term = chunk.trim();
    const normalized = normalizeTerm(term);
    if (!normalized || seen.has(normalized)) {
      continue;
    }
    seen.set(normalized, term);
  }
  return [...seen.values()];
}

function collectText(draft: TopicAnalysisDraft) {
  return [draft.title, draft.summary, draft.requirements, draft.keywords]
    .map((item) => item.trim())
    .filter(Boolean)
    .join(" ");
}

function containsAny(text: string, candidates: string[]) {
  const source = normalizeTerm(text);
  return candidates.some((candidate) => source.includes(normalizeTerm(candidate)));
}

const capabilityRules = [
  {
    label: "前端实现与交互设计",
    signals: ["react", "前端", "ui", "交互", "页面", "workbench"],
  },
  {
    label: "后端接口与数据建模",
    signals: ["flask", "python", "后端", "接口", "数据库", "api"],
  },
  {
    label: "模型调用与语义分析",
    signals: ["llm", "大模型", "ai", "推荐", "画像", "关键词", "prompt", "语义"],
  },
  {
    label: "文档处理与内容理解",
    signals: ["pdf", "文档", "解析", "摘要", "分块"],
  },
  {
    label: "异步任务编排与状态流转",
    signals: ["异步", "队列", "任务", "worker", "状态"],
  },
  {
    label: "学术写作与实验整理",
    signals: ["论文", "学术", "文献", "实验", "答辩"],
  },
];

function uniqueList(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

function buildCapabilities(text: string) {
  const matches = capabilityRules
    .filter((rule) => containsAny(text, rule.signals))
    .map((rule) => rule.label);

  if (matches.length) {
    return matches;
  }

  return ["需求分析与阶段推进"];
}

function buildDifficultyLabel(capabilities: string[], draft: TopicAnalysisDraft) {
  const keywordCount = parseWorkbenchTerms(draft.keywords).length;
  const textLength = draft.summary.length + draft.requirements.length;
  const score =
    capabilities.length +
    (keywordCount >= 4 ? 1 : 0) +
    (textLength > 120 ? 1 : 0) +
    (textLength > 220 ? 1 : 0);

  if (score >= 5) {
    return {
      difficultyLabel: "挑战" as const,
      difficultyReason: "题目覆盖多个能力域，适合拆成阶段里程碑推进。",
    };
  }

  if (score >= 3) {
    return {
      difficultyLabel: "进阶" as const,
      difficultyReason: "题目需要一定的工程整合能力，建议提前规划任务拆分。",
    };
  }

  return {
    difficultyLabel: "基础" as const,
    difficultyReason: "题目边界较清晰，适合按模块逐步实现。",
  };
}

export function buildTopicAnalysis(draft: TopicAnalysisDraft): TopicAnalysisResult {
  const focusKeywords = uniqueList([
    ...parseWorkbenchTerms(draft.keywords),
    ...buildCapabilities(collectText(draft)).slice(0, 2),
  ]).slice(0, 6);
  const requiredCapabilities = buildCapabilities(collectText(draft));
  const difficulty = buildDifficultyLabel(requiredCapabilities, draft);
  const summarySeed = focusKeywords.length ? focusKeywords.join("、") : draft.title.trim() || "题目目标";

  return {
    focusKeywords,
    difficultyLabel: difficulty.difficultyLabel,
    difficultyReason: difficulty.difficultyReason,
    requiredCapabilities,
    suitableStudents: uniqueList([
      difficulty.difficultyLabel === "挑战" ? "有完整项目经验、能持续投入的学生" : "",
      requiredCapabilities.includes("模型调用与语义分析")
        ? "对大模型、提示词或推荐解释感兴趣的学生"
        : "",
      requiredCapabilities.includes("前端实现与交互设计")
        ? "希望做出可答辩展示交互界面的学生"
        : "",
      requiredCapabilities.includes("后端接口与数据建模")
        ? "熟悉接口联调和数据组织的学生"
        : "",
    ]).slice(0, 3),
    risks: uniqueList([
      requiredCapabilities.length > 2 ? "跨模块较多，建议先固定边界再实现主链路。" : "",
      requiredCapabilities.includes("异步任务编排与状态流转")
        ? "异步状态需要明确终态回写与失败兜底。"
        : "",
      requiredCapabilities.includes("模型调用与语义分析")
        ? "推荐结果需要可解释字段，避免黑盒输出。"
        : "",
    ]).slice(0, 3),
    milestoneHints: [
      "先确认题目画像字段，再做推荐依据。",
      "把分析结果拆成标签、理由和风险三层展示。",
      "答辩时优先展示老师分析和学生推荐的闭环。",
    ],
    demoHighlights: [
      "输入题目后生成结构化画像",
      "输出适合学生类型与风险点",
      "保留推荐解释字段，便于答辩演示",
    ],
    summary: `围绕 ${summarySeed} 展开，系统会把题目拆成关键词、能力要求、适配学生类型和风险提示，方便后续推荐。`,
  };
}

function topicTermSet(topic: Topic) {
  return uniqueList([
    ...topic.techKeywords,
    ...(topic.portrait?.keywords ?? []),
  ]).map((term) => term.trim()).filter(Boolean);
}

function parseProfileTerms(profile: StudentProfileDraft) {
  return uniqueList([
    ...parseWorkbenchTerms(profile.interests),
    ...parseWorkbenchTerms(profile.skills),
    ...parseWorkbenchTerms(profile.keywords),
    ...parseWorkbenchTerms(profile.goal),
  ]);
}

function matchesProfileTerm(topicTerm: string, profileTerms: string[]) {
  const topicNormalized = normalizeTerm(topicTerm);
  return profileTerms.some((profileTerm) => {
    const profileNormalized = normalizeTerm(profileTerm);
    return (
      profileNormalized.includes(topicNormalized) ||
      topicNormalized.includes(profileNormalized)
    );
  });
}

export function buildTopicRecommendations(
  topics: Topic[],
  profile: StudentProfileDraft,
) {
  const profileTerms = parseProfileTerms(profile);
  const profileTermsLower = profileTerms.map((term) => normalizeTerm(term));
  const hours = Number(profile.weeklyHours.trim());
  const normalizedHours = Number.isFinite(hours) ? hours : 0;

  const scored = topics
    .filter((topic) => topic.status === "published")
    .map((topic) => {
      const terms = topicTermSet(topic);
      const matchedTerms = terms.filter((term) => matchesProfileTerm(term, profileTermsLower));
      const remainingCapacity = Math.max(topic.capacity - topic.selectedCount, 0);
      let score = 34 + matchedTerms.length * 18;
      score += remainingCapacity > 0 ? 12 : -20;
      score += topic.portrait?.keywords?.length ? 6 : 0;
      score += normalizedHours >= 8 ? 4 : 0;
      score = Math.max(0, Math.min(98, score));

      const reasons = uniqueList([
        matchedTerms.length ? `匹配到关键词：${matchedTerms.slice(0, 3).join("、")}` : "",
        remainingCapacity > 0
          ? `当前仍有 ${remainingCapacity} 个名额`
          : "题目容量已满，优先级会被下调",
        topic.portrait?.keywords?.length
          ? "题目已形成系统画像，可解释性更强"
          : "",
      ]);

      const warning =
        remainingCapacity <= 0
          ? "该题目容量已满"
          : matchedTerms.length === 0
            ? "与当前输入的兴趣和技能重合较少"
            : normalizedHours > 0 && normalizedHours < 6 && topic.requirements.length > 50
              ? "题目要求较多，建议评估每周投入时间"
              : null;

      return {
        topic,
        score,
        matchedTerms,
        reasons,
        warning,
      };
    });

  scored.sort((left, right) => {
    if (right.score !== left.score) {
      return right.score - left.score;
    }
    return left.topic.title.localeCompare(right.topic.title, "zh-Hans-CN");
  });

  return scored;
}
