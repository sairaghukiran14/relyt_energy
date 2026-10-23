import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, proxy /api to the FastAPI backend so the front end and API share an
// origin (matching the single-origin Vercel setup in production: no CORS).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
