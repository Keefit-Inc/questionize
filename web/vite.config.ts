import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  // The production image serves the built app from Rails' public/ directory.
  build: { outDir: "dist", emptyOutDir: true, assetsDir: "web-assets" },
  server: { proxy: { "/api": "http://localhost:3000", "/cable": { target: "ws://localhost:3000", ws: true } } },
  test: { environment: "jsdom" },
});
