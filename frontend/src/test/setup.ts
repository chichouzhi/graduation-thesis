import { afterEach } from "vitest";

afterEach(() => {
  globalThis.localStorage?.clear();
});
