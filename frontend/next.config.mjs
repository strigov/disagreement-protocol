import { fileURLToPath } from "node:url";

const desktopBuild = process.env.DISPROT_DESKTOP_BUILD === "1";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Desktop packages include Next's minimal server and its traced dependencies.
  ...(desktopBuild ? { output: "standalone" } : {}),
  outputFileTracingRoot: fileURLToPath(new URL(".", import.meta.url)),
  env: { DISPROT_UI_PORT: desktopBuild ? "17341" : "3000" },
  reactStrictMode: true,
  // One extra MiB above the backend's cap lets it return 413 for chunked bodies.
  experimental: { middlewareClientMaxBodySize: "27mb" },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `http://127.0.0.1:${desktopBuild ? 17342 : 8000}/api/:path*` },
    ];
  },
};

export default nextConfig;
