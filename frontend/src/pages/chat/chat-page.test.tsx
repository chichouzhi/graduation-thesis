import { StrictMode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

const createConversation = vi.fn();

vi.mock("@/app/store", () => ({
  useAppStore: (selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      isAuthenticated: true,
      currentUser: {
        id: "student-1",
        username: "student-demo",
        role: "student",
        display_name: "联调学生",
      },
      currentTerm: {
        id: "term-2026-spring",
        name: "2026 春季学期",
      },
    }),
}));

vi.mock("@/components/ui/scroll-area", () => ({
  ScrollArea: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/features/chat/chat.queries", () => ({
  useConversationsQuery: () => ({
    data: { items: [] },
    isSuccess: true,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateConversationMutation: () => ({
    mutate: createConversation,
    data: undefined,
    isPending: false,
    isError: false,
    error: null,
  }),
  useMessagesQuery: () => ({
    data: { items: [] },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  usePostMessageMutation: () => ({
    mutate: vi.fn(),
    data: undefined,
    isPending: false,
  }),
  useChatJobQuery: () => ({
    data: undefined,
    isError: false,
    error: null,
  }),
}));

describe("ChatPage", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    createConversation.mockClear();
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("only auto-creates one fallback conversation when none exist", async () => {
    const { ChatPage } = await import("@/pages/chat/chat-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <ChatPage />
        </StrictMode>,
      );
    });

    expect(createConversation).toHaveBeenCalledTimes(1);
    expect(createConversation).toHaveBeenCalledWith({
      term_id: "term-2026-spring",
      title: "通用学术咨询",
      context_type: "general",
    });

    await act(async () => {
      root.unmount();
    });
  });

  it("creates a new general conversation from the toolbar button", async () => {
    const { ChatPage } = await import("@/pages/chat/chat-page");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <StrictMode>
          <ChatPage />
        </StrictMode>,
      );
    });

    const createButton = container.querySelector<HTMLButtonElement>('button[aria-label="新建会话"]');
    expect(createButton).not.toBeNull();

    await act(async () => {
      createButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(createConversation).toHaveBeenCalledWith({
      term_id: "term-2026-spring",
      title: "新建学术咨询",
      context_type: "general",
    });

    await act(async () => {
      root.unmount();
    });
  });
});
