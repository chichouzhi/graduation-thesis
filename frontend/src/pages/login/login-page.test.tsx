import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock("@/app/store", () => ({
  useAppStore: (selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      login: vi.fn(),
    }),
}));

vi.mock("@/features/auth/auth.api", () => ({
  login: vi.fn(),
}));

describe("LoginPage", () => {
  let container: HTMLDivElement;
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    queryClient.clear();
  });

  it("does not prefill demo credentials until the student chooses the demo account", async () => {
    const { LoginPage } = await import("@/pages/login/login-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <QueryClientProvider client={queryClient}>
            <LoginPage />
          </QueryClientProvider>
        </StrictMode>,
      );
    });

    const usernameInput = container.querySelector<HTMLInputElement>("#student-id");
    const passwordInput = container.querySelector<HTMLInputElement>("#password");

    expect(usernameInput?.value).toBe("");
    expect(passwordInput?.value).toBe("");

    const demoButton = Array.from(container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("填入演示账号"),
    );
    expect(demoButton).toBeTruthy();

    await act(async () => {
      demoButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(usernameInput?.value).toBe("api-login-user");
    expect(passwordInput?.value).toBe("correct-pass");

    await act(async () => {
      root.unmount();
    });
  });
});
