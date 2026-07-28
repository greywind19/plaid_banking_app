import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The UI calls the REST API on :8787. We proxy /api during dev so there are no
// CORS surprises and the frontend can just fetch("/api/...").
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8787",
        changeOrigin: true,
      },
    },
  },
});
