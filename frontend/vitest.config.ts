import { configDefaults, defineConfig, mergeConfig } from "vitest/config";

import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      clearMocks: true,
      environment: "jsdom",
      environmentOptions: {
        jsdom: {
          url: "http://localhost:5173/",
        },
      },
      exclude: [...configDefaults.exclude, "e2e/**"],
      restoreMocks: true,
      setupFiles: ["./src/test/setup.ts"],
    },
  }),
);
