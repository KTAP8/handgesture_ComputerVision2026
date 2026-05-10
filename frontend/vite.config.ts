import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // In development, forward all Flask API routes to port 5001
    // so the React dev server and Flask can run side by side.
    proxy: {
      "/gesture":  "http://localhost:5001",
      "/stream":   "http://localhost:5001",
      "/dispatch": "http://localhost:5001",
      "/bind":     "http://localhost:5001",
    },
  },
});
