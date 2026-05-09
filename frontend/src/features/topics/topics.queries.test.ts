import { describe, expect, it } from "vitest";

import { getTopicPollingInterval } from "@/features/topics/topics.queries";

describe("topics.queries", () => {
  it("keeps polling while topic analysis is active", () => {
    expect(getTopicPollingInterval("pending")).toBe(2000);
    expect(getTopicPollingInterval("running")).toBe(2000);
  });

  it("stops polling after topic analysis reaches a terminal state", () => {
    expect(getTopicPollingInterval("done")).toBe(false);
    expect(getTopicPollingInterval("failed")).toBe(false);
    expect(getTopicPollingInterval(null)).toBe(false);
  });
});
