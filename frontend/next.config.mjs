/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // One extra MiB above the backend's cap lets it return 413 for chunked bodies.
  experimental: { middlewareClientMaxBodySize: "27mb" },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
    ];
  },
};

export default nextConfig;
