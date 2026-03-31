import type { NextConfig } from "next";

const proxyTarget =
  process.env.API_PROXY_TARGET?.replace(/\/$/, "") ?? "http://127.0.0.1:5000";

if (
  process.env.VERCEL &&
  !process.env.API_PROXY_TARGET?.trim() &&
  !process.env.NEXT_PUBLIC_API_URL?.trim()
) {
  console.warn(
    "[next.config] Vercel: set API_PROXY_TARGET (Option 2) or NEXT_PUBLIC_API_URL (Option 1) on the web project so /api/* reaches Flask. See docs/VERCEL_WIRE_NEXT_API.md"
  );
}

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${proxyTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
