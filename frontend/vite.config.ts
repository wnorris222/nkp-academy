import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy API + ops endpoints to the FastAPI backend so the SPA and API
// share an origin (mirrors production, where FastAPI serves the built SPA).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/healthz": "http://localhost:8000",
      "/metrics": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
