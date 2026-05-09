import type { PatchUserMeRequest, StudentProfile } from "@/features/users/users.types";

export type TeacherTopicDraft = {
  title: string;
  summary: string;
  requirements: string;
  keywords: string;
  capacity: string;
};

export type StudentProfileDraft = {
  interests: string;
  skills: string;
  keywords: string;
  goal: string;
  weeklyHours: string;
};

const splitPattern = /[\n,，、;；/|]+/;

export function parseDraftTerms(text: string) {
  const seen = new Map<string, string>();

  for (const chunk of text.split(splitPattern)) {
    const term = chunk.trim();
    const normalized = term.toLowerCase();

    if (!normalized || seen.has(normalized)) {
      continue;
    }

    seen.set(normalized, term);
  }

  return [...seen.values()];
}

export function buildCreateTopicRequest(draft: TeacherTopicDraft, termId: string) {
  return {
    title: draft.title.trim(),
    summary: draft.summary.trim(),
    requirements: draft.requirements.trim(),
    tech_keywords: parseDraftTerms(draft.keywords),
    capacity: Math.max(1, Number(draft.capacity.trim()) || 1),
    term_id: termId,
  };
}

export function buildPatchTopicRequest(draft: TeacherTopicDraft) {
  return {
    title: draft.title.trim(),
    summary: draft.summary.trim(),
    requirements: draft.requirements.trim(),
    tech_keywords: parseDraftTerms(draft.keywords),
    capacity: Math.max(1, Number(draft.capacity.trim()) || 1),
  };
}

export function mapStudentProfileToDraft(profile?: StudentProfile) {
  return {
    interests: profile?.interests?.join("，") ?? "",
    skills: profile?.skills?.join("，") ?? "",
    keywords: profile?.keywords?.join("，") ?? "",
    goal: profile?.goal ?? "",
    weeklyHours:
      typeof profile?.weeklyHours === "number" ? String(profile.weeklyHours) : "",
  };
}

export function buildStudentProfilePatch(
  draft: StudentProfileDraft,
): PatchUserMeRequest {
  const weeklyHours = Number(draft.weeklyHours.trim());

  return {
    student_profile: {
      interests: parseDraftTerms(draft.interests),
      skills: parseDraftTerms(draft.skills),
      keywords: parseDraftTerms(draft.keywords),
      goal: draft.goal.trim() || null,
      weekly_hours: Number.isFinite(weeklyHours) ? weeklyHours : null,
    },
  };
}
