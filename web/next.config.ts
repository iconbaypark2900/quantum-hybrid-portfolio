import type { NextConfig } from "next";

// `/api/*` is proxied at request time by `src/app/api/[[...path]]/route.ts` using
// `process.env.API_PROXY_TARGET` (Fly secrets, Vercel env, or web/.env.local).
// Do not use next.config rewrites for Flask — they are baked at `next build`.

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
