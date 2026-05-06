import { create } from "zustand";

type UserSummary = {
  id: string;
  name: string;
  role: "student";
  studentNo: string;
};

type TermSummary = {
  id: string;
  name: string;
};

type AppState = {
  isAuthenticated: boolean;
  currentUser: UserSummary;
  currentTerm: TermSummary;
  login: () => void;
  logout: () => void;
};

export const useAppStore = create<AppState>((set) => ({
  isAuthenticated: false,
  currentUser: {
    id: "student-001",
    name: "刘佳浩",
    role: "student",
    studentNo: "20220001",
  },
  currentTerm: {
    id: "term-2026-spring",
    name: "2026 春季学期",
  },
  login: () => set({ isAuthenticated: true }),
  logout: () => set({ isAuthenticated: false }),
}));
