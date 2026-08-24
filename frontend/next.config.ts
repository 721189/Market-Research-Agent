import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      // Proxy API + SSE + PDF calls to the FastAPI backend on :8000.
      // The Next.js dev/prod server serves the UI on :3000 and forwards
      // /api/* to the Python service so the browser never hits CORS.
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
