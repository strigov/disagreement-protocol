import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  root: path.resolve(__dirname, "desktop"),
  publicDir: false,
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
      "next/navigation": path.resolve(__dirname, "desktop/navigation.tsx"),
      "next/link": path.resolve(__dirname, "desktop/navigation.tsx"),
    },
  },
  css: { postcss: path.resolve(__dirname, ".") },
  build: {
    outDir: path.resolve(__dirname, "../desktop/build/ui"),
    emptyOutDir: true,
  },
});
