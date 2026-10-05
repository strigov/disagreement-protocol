import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  root: path.resolve(__dirname, "desktop"),
  publicDir: path.resolve(__dirname, "public"),
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  css: { postcss: path.resolve(__dirname, ".") },
  build: {
    outDir: path.resolve(__dirname, "../desktop/build/ui"),
    emptyOutDir: true,
  },
});
