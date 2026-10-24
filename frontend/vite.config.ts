import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, proxy /api to the FastAPI backend so the front end and API share an
// origin (matching the single-origin Vercel setup in production: no CORS).
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Split heavy vendor code so the app chunk stays small and caches separately.
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          charts: ["recharts"],
        },
      },
    },
  },
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
