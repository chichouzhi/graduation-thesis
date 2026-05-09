import type { AuthSession } from "@/features/auth/auth.types";

const AUTH_STORAGE_KEY = "frontend.auth.session";

export function loadAuthSession(): AuthSession | null {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);

  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<AuthSession>;

    if (
      typeof parsed.accessToken !== "string" ||
      typeof parsed.expiresIn !== "number" ||
      !parsed.user ||
      typeof parsed.user.username !== "string" ||
      typeof parsed.user.role !== "string"
    ) {
      return null;
    }

    return parsed as AuthSession;
  } catch {
    return null;
  }
}

export function saveAuthSession(session: AuthSession) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function clearAuthSession() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}
