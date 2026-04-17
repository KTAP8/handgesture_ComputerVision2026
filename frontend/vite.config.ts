import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/gesture": "http://localhost:5001",
      "/stream":  "http://localhost:5001",
    },
  },
});
