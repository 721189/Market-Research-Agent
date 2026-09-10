import { NextRequest, NextResponse } from "next/server";
import { verifyAuth } from "../../../../lib/auth";

const FASTAPI_URL = process.env.FASTAPI_URL || "http://127.0.0.1:8000";

/**
 * BFF Proxy to Authoritative FastAPI Research Job Status (Phase 0 & 21)
 */
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ task_id: string }> }
) {
  try {
    const user = await verifyAuth(req);
    const { task_id } = await params;
    const { searchParams } = new URL(req.url);
    const orgId = searchParams.get("orgId") || "";

    const authHeader = req.headers.get("authorization") || "";

    try {
      const fastApiResponse = await fetch(`${FASTAPI_URL}/api/v1/research/${encodeURIComponent(task_id)}`, {
        method: "GET",
        headers: {
          "Authorization": authHeader,
          "X-Organization-ID": orgId,
          "X-User-ID": user?.uid || "",
        },
      });

      if (fastApiResponse.ok) {
        const data = await fastApiResponse.json();
        return NextResponse.json({
          status: data.status,
          task_id: data.task_id,
          progress: data.progress,
          result: data.result || null,
          pdf_ready: data.pdf_ready || false,
          pdf_download_url: data.pdf_download_url || null,
          error: data.error_message || null,
        });
      }

      if (fastApiResponse.status === 404) {
        return NextResponse.json({ status: "FAILURE", task_id, error: "Task not found" }, { status: 404 });
      }
    } catch (fetchErr: unknown) {
      const msg = fetchErr instanceof Error ? fetchErr.message : "Network error";
      console.error("FastAPI unreachable from Next.js BFF proxy:", msg);
      return NextResponse.json({
        status: "FAILED",
        task_id,
        error: "Authoritative research backend is unreachable. Unable to retrieve job status.",
        code: "BACKEND_UNAVAILABLE"
      }, { status: 503 });
    }

    return NextResponse.json({
      status: "FAILED",
      task_id,
      error: "Unexpected response state from upstream research engine.",
      code: "UPSTREAM_ERROR"
    }, { status: 502 });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Internal error";
    return NextResponse.json({ status: "FAILURE", error: message }, { status: 500 });
  }
}
