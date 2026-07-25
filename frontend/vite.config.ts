import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite configuration for OpsForge frontend with API proxy to FastAPI backend
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
