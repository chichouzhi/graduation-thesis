import { create } from "zustand";

import { clearAuthSession, loadAuthSession, saveAuthSession } from "@/features/auth/auth.storage";
import type { AuthSession, AuthUser } from "@/features/auth/auth.types";

type TermSummary = {
  id: string;
  name: string;
};

type AppState = {
  isAuthReady: boolean;
  isAuthenticated: boolean;
  accessToken: string | null;
  currentUser: AuthUser | null;
  currentTerm: TermSummary;
  hydrateAuth: () => void;
  login: (session: AuthSession) => void;
  logout: () => void;
};

export const useAppStore = create<AppState>((set) => ({
  isAuthReady: false,
  isAuthenticated: false,
  accessToken: null,
  currentUser: null,
  currentTerm: {
    id: "term-2026-spring",
    name: "2026 春季学期",
  },
  hydrateAuth: () => {
    const session = loadAuthSession();

    if (!session) {
      set({
        isAuthReady: true,
        isAuthenticated: false,
        accessToken: null,
        currentUser: null,
      });
      return;
    }

    set({
      isAuthReady: true,
      isAuthenticated: true,
      accessToken: session.accessToken,
      currentUser: session.user,
    });
  },
  login: (session) => {
    saveAuthSession(session);
    set({
      isAuthReady: true,
      isAuthenticated: true,
      accessToken: session.accessToken,
      currentUser: session.user,
    });
  },
  logout: () => {
    clearAuthSession();
    set({
      isAuthReady: true,
      isAuthenticated: false,
      accessToken: null,
      currentUser: null,
    });
  },
}));
