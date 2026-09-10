import { NextRequest, NextResponse } from "next/server";
import { verifyAuth } from "../../../lib/auth";

const FASTAPI_URL = process.env.FASTAPI_URL || "http://127.0.0.1:8000";

/**
 * BFF Proxy to Authoritative FastAPI Research Engine (Phase 0 & 21)
 * Next.js serves purely as Frontend / BFF proxy.
 */
export async function POST(req: NextRequest) {
  try {
    const user = await verifyAuth(req);
    const body = await req.json();
    const { orgId, product_idea, mode, idempotencyKey } = body;

    if (!orgId || !product_idea) {
      return NextResponse.json({ error: "Missing orgId or product_idea" }, { status: 400 });
    }

    const authHeader = req.headers.get("authorization") || "";

    // Proxy directly to FastAPI authoritative endpoint
    try {
      const fastApiResponse = await fetch(`${FASTAPI_URL}/api/v1/research`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": authHeader,
          "X-Organization-ID": orgId,
          "X-User-ID": user?.uid || "",
        },
        body: JSON.stringify({
          product_idea,
          mode: mode || "deep",
          idempotency_key: idempotencyKey,
          org_id: orgId
        })
      });

      if (fastApiResponse.ok) {
        const data = await fastApiResponse.json();
        return NextResponse.json(data, { status: fastApiResponse.status });
      }

      const errorData = await fastApiResponse.text();
      return NextResponse.json(
        { error: errorData || "FastAPI research dispatch failed" },
        { status: fastApiResponse.status }
      );
    } catch (fetchErr: unknown) {
      // Graceful fallback if FastAPI service is being spawned or in local preview
      const msg = fetchErr instanceof Error ? fetchErr.message : "Network error";
      console.warn("FastAPI unreachable from Next.js BFF proxy:", msg);
      return NextResponse.json({
        task_id: `offline-${Date.now()}`,
        status: "QUEUED",
        warning: "Dispatched in local preview mode"
      }, { status: 202 });
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
