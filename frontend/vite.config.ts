import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const frontendPort = Number(process.env.REVIEWER_FRONTEND_PORT || 5174);
const previewPort = Number(process.env.REVIEWER_FRONTEND_PREVIEW_PORT || 4174);
const apiTarget = process.env.REVIEWER_API_TARGET || "http://127.0.0.1:8011";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: frontendPort,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: previewPort,
  },
});
