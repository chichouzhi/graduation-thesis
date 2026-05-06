import { AxiosError } from "axios";
import { describe, expect, it } from "vitest";

import { getErrorMessage, parseApiError } from "@/lib/api-error";

describe("parseApiError", () => {
  it("reads ErrorEnvelope fields", () => {
    const error = new AxiosError("Request failed", "400", undefined, undefined, {
      data: {
        error: {
          code: "VALIDATION_ERROR",
          message: "username and password are required",
          details: { field: "username" },
        },
      },
      status: 400,
      statusText: "Bad Request",
      headers: {},
      config: {} as never,
    });

    expect(parseApiError(error)).toEqual({
      code: "VALIDATION_ERROR",
      message: "username and password are required",
      details: { field: "username" },
      status: 400,
    });
  });

  it("falls back to generic message", () => {
    expect(getErrorMessage(new Error("boom"), "默认文案")).toBe("boom");
  });
});
