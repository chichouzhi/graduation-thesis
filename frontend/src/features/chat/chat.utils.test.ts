import { describe, expect, it } from "vitest";

import { isAsyncTaskTerminal, shouldPollChatJob } from "@/features/chat/chat.utils";

describe("chat.utils", () => {
  it("treats done and failed as terminal", () => {
    expect(isAsyncTaskTerminal("done")).toBe(true);
    expect(isAsyncTaskTerminal("failed")).toBe(true);
  });

  it("keeps polling for pending and running only", () => {
    expect(shouldPollChatJob("pending")).toBe(true);
    expect(shouldPollChatJob("running")).toBe(true);
    expect(shouldPollChatJob("done")).toBe(false);
    expect(shouldPollChatJob("failed")).toBe(false);
  });
});
