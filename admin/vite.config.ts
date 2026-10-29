import { readFile } from "node:fs/promises";
import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue(), {
    name: "local-research-data",
    configureServer(server) {
      server.middlewares.use("/admin/data", async (_request, response) => {
        try {
          response.setHeader("Content-Type", "application/json");
          response.setHeader("Cache-Control", "no-store");
          response.end(await readFile(new URL("../research/results/dashboard.json", import.meta.url), "utf8"));
        } catch {
          response.statusCode = 503;
          response.end(JSON.stringify({ error: "Run python -m questionize.scoreboard first." }));
        }
      });
    },
  }],
  build: { assetsDir: "admin-assets" },
  test: { environment: "jsdom" },
});
