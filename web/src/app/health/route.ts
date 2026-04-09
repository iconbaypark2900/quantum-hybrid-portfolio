import { NextResponse } from "next/server";

/** Fly.io / load balancer liveness — must return 2xx (root `/` redirects, so it is not suitable). */
export function GET() {
  return NextResponse.json({ status: "ok" }, { status: 200 });
}
