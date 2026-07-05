import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { server } from "./server";

const nativeFetch = globalThis.fetch;

globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
  const resolvedInput =
    typeof input === "string" && input.startsWith("/")
      ? new URL(input, window.location.origin)
      : input;
  return nativeFetch(resolvedInput, init);
}) as typeof globalThis.fetch;

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
  server.resetHandlers();
  cleanup();
});

afterAll(() => {
  server.close();
  globalThis.fetch = nativeFetch;
});
