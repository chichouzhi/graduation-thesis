import { beforeEach, describe, expect, it } from "vitest";

import {
  clearAuthSession,
  loadAuthSession,
  saveAuthSession,
} from "@/features/auth/auth.storage";
import type { AuthSession } from "@/features/auth/auth.types";

const session: AuthSession = {
  accessToken: "token-123",
  expiresIn: 3600,
  user: {
    id: "user-1",
    username: "student-a",
    role: "student",
    display_name: "Student A",
  },
};

describe("auth.storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("saves and loads auth session", () => {
    saveAuthSession(session);
    expect(loadAuthSession()).toEqual(session);
  });

  it("returns null for invalid payload", () => {
    localStorage.setItem("frontend.auth.session", "{bad json");
    expect(loadAuthSession()).toBeNull();
  });

  it("clears persisted session", () => {
    saveAuthSession(session);
    clearAuthSession();
    expect(loadAuthSession()).toBeNull();
  });
});
