import { NextRequest, NextResponse } from "next/server";

/**
 * Server-side proxy to the Flask API. Reads `API_PROXY_TARGET` at **request time**
 * (Fly `fly secrets`, Vercel server env, `web/.env.local`) — unlike `next.config` rewrites,
 * which are compiled at build time.
 *
 * When `NEXT_PUBLIC_API_URL` is set, the browser talks to Flask directly (Option 1); this
 * route is unused for those clients.
 */

export const dynamic = "force-dynamic";
export const maxDuration = 300;

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
]);

const FETCH_TIMEOUT_MS = 120_000;

/** Default Flask app name on Fly (see repo root `fly.toml` `app =`). Override via API_PROXY_TARGET or API_UPSTREAM_FLY_APP. */
const DEFAULT_FLY_API_APP = "quantum-hybrid-portfolio";

function backendBase(): string {
  const explicit = process.env.API_PROXY_TARGET?.trim();
  if (explicit) return explicit.replace(/\/$/, "");

  // On Fly Machines, never default to localhost — there is no Flask on :5000 in this container.
  if (process.env.FLY_APP_NAME) {
    const app =
      process.env.API_UPSTREAM_FLY_APP?.trim() || DEFAULT_FLY_API_APP;
    return `http://${app}.internal:5000`;
  }

  return "http://127.0.0.1:5000";
}

function sanitizeUpstreamHeaders(res: Response): Headers {
  const out = new Headers(res.headers);
  for (const h of ["connection", "transfer-encoding", "keep-alive"]) {
    out.delete(h);
  }
  return out;
}

function buildTargetUrl(pathSegments: string[], search: string): URL {
  const path = pathSegments.length ? pathSegments.join("/") : "";
  const suffix = path ? `/api/${path}` : "/api";
  return new URL(`${backendBase()}${suffix}${search}`);
}

async function proxy(req: NextRequest, pathSegments: string[]) {
  const targetUrl = buildTargetUrl(pathSegments, req.nextUrl.search);
  const headers = new Headers();
  req.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (HOP_BY_HOP.has(k)) return;
    if (k === "host") return;
    headers.set(key, value);
  });

  const init: RequestInit = {
    method: req.method,
    headers,
    redirect: "manual",
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    const buf = await req.arrayBuffer();
    if (buf.byteLength) init.body = buf;
  }

  const res = await fetch(targetUrl, init);
  return new NextResponse(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: sanitizeUpstreamHeaders(res),
  });
}

type RouteContext = { params: Promise<{ path?: string[] }> };

async function handle(req: NextRequest, ctx: RouteContext) {
  const { path = [] } = await ctx.params;
  try {
    return await proxy(req, path);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    const base = backendBase();
    console.error("[api proxy] fetch failed", { base, message: msg });
    return NextResponse.json(
      {
        error: {
          code: "PROXY_ERROR",
          message: `Upstream proxy failed: ${msg}. Check API app is running and reachable at ${base}.`,
        },
      },
      { status: 502 }
    );
  }
}

export function GET(req: NextRequest, ctx: RouteContext) {
  return handle(req, ctx);
}
export function HEAD(req: NextRequest, ctx: RouteContext) {
  return handle(req, ctx);
}
export function POST(req: NextRequest, ctx: RouteContext) {
  return handle(req, ctx);
}
export function PUT(req: NextRequest, ctx: RouteContext) {
  return handle(req, ctx);
}
export function PATCH(req: NextRequest, ctx: RouteContext) {
  return handle(req, ctx);
}
export function DELETE(req: NextRequest, ctx: RouteContext) {
  return handle(req, ctx);
}
export function OPTIONS(req: NextRequest, ctx: RouteContext) {
  return handle(req, ctx);
}
