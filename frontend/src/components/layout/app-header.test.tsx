import { StrictMode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

const logout = vi.fn();
const navigate = vi.fn();

vi.mock("@/app/store", () => ({
  useAppStore: () => ({
    currentTerm: {
      id: "term-2026-spring",
      name: "2026 春季学期",
    },
    currentUser: {
      id: "student-1",
      username: "api-login-user",
      role: "student",
      display_name: "联调学生",
    },
    logout,
  }),
}));

vi.mock("react-router-dom", () => ({
  useLocation: () => ({ pathname: "/app/chat" }),
  useNavigate: () => navigate,
}));

describe("AppHeader", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    logout.mockClear();
    navigate.mockClear();
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("shows a Chinese page title and logs out back to login", async () => {
    const { AppHeader } = await import("@/components/layout/app-header");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <AppHeader />
        </StrictMode>,
      );
    });

    expect(container.querySelector("h1")?.textContent).toBe("AI 对话");

    const logoutButton = Array.from(container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("退出"),
    );
    expect(logoutButton).toBeTruthy();

    await act(async () => {
      logoutButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(logout).toHaveBeenCalledTimes(1);
    expect(navigate).toHaveBeenCalledWith("/login", { replace: true });

    await act(async () => {
      root.unmount();
    });
  });
});
