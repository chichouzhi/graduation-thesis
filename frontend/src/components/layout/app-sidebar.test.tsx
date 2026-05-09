import { StrictMode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

describe("AppSidebar", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("uses student-facing Chinese navigation labels", async () => {
    const { AppSidebar } = await import("@/components/layout/app-sidebar");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <MemoryRouter initialEntries={["/app/dashboard"]}>
            <AppSidebar />
          </MemoryRouter>
        </StrictMode>,
      );
    });

    expect(container.textContent).toContain("工作台");
    expect(container.textContent).toContain("AI 对话");
    expect(container.textContent).toContain("文档分析");
    expect(container.textContent).toContain("选题中心");
    expect(container.textContent).toContain("任务看板");
    expect(container.textContent).not.toContain("Dashboard");

    await act(async () => {
      root.unmount();
    });
  });
});
