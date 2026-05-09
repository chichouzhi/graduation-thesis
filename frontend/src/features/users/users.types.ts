import type { UserRole } from "@/features/auth/auth.types";

export type StudentProfileDto = {
  interests?: string[];
  skills?: string[];
  keywords?: string[];
  goal?: string | null;
  weekly_hours?: number | null;
} | null;

export type StudentProfile = {
  interests: string[];
  skills: string[];
  keywords: string[];
  goal: string | null;
  weeklyHours: number | null;
} | null;

export type UserMeDto = {
  id: string;
  username: string;
  role: UserRole;
  display_name: string;
  email?: string | null;
  student_profile?: StudentProfileDto;
  teacher_profile?: Record<string, unknown> | null;
};

export type UserMe = {
  id: string;
  username: string;
  role: UserRole;
  displayName: string;
  email: string | null;
  studentProfile?: StudentProfile;
  teacherProfile: Record<string, unknown> | null;
};

export type PatchUserMeRequest = {
  display_name?: string;
  email?: string;
  student_profile?: {
    interests?: string[];
    skills?: string[];
    keywords?: string[];
    goal?: string | null;
    weekly_hours?: number | null;
  } | null;
};

export function mapStudentProfileDto(profile?: StudentProfileDto): StudentProfile | undefined {
  if (profile === undefined) {
    return undefined;
  }

  if (profile === null) {
    return null;
  }

  return {
    interests: profile.interests ?? [],
    skills: profile.skills ?? [],
    keywords: profile.keywords ?? [],
    goal: profile.goal ?? null,
    weeklyHours: profile.weekly_hours ?? null,
  };
}

export function mapUserMeDto(user: UserMeDto): UserMe {
  return {
    id: user.id,
    username: user.username,
    role: user.role,
    displayName: user.display_name,
    email: user.email ?? null,
    studentProfile: mapStudentProfileDto(user.student_profile),
    teacherProfile: user.teacher_profile ?? null,
  };
}
