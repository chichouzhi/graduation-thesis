import { describe, expect, it } from "vitest";

import { router } from "@/routes";

describe("router", () => {
  it("uses friendly route error fallbacks for public and app routes", () => {
    const loginRoute = router.routes.find((route) => route.path === "/login");
    const appRoute = router.routes.find((route) => route.path === "/app");

    expect(loginRoute?.errorElement).toBeTruthy();
    expect(appRoute?.errorElement).toBeTruthy();
  });
});
