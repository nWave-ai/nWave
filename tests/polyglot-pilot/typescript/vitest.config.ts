import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
    reporters: ["default"],
    // Fail-loud — surface unhandled rejections instead of silently passing.
    dangerouslyIgnoreUnhandledErrors: false,
  },
});
