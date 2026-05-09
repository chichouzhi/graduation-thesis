import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { saveAuthSession } from "@/features/auth/auth.storage";

const navigateSpy = vi.fn();

vi.mock("react-router-dom", () => ({
  Navigate: ({ to }: { to: string }) => <div data-kind="navigate">{to}</div>,
  Outlet: () => <div data-kind="outlet">outlet</div>,
}));

vi.mock("@/components/layout/app-shell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => (
    <div data-kind="app-shell">{children}</div>
  ),
}));

describe("ProtectedLayout", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    vi.resetModules();
    localStorage.clear();
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    navigateSpy.mockReset();
  });

  it("renders app shell after auth hydration without causing update loops", async () => {
    saveAuthSession({
      accessToken: "token-1",
      expiresIn: 3600,
      user: {
        id: "user-1",
        username: "api-login-user",
        role: "student",
        display_name: "联调学生",
      },
    });

    const { AppProviders } = await import("@/app/providers");
    const { ProtectedLayout } = await import("@/routes/protected-layout");

    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <AppProviders>
            <ProtectedLayout />
          </AppProviders>
        </StrictMode>,
      );
    });

    expect(container.querySelector('[data-kind="app-shell"]')?.textContent).toContain("outlet");
    root.unmount();
  });
});
