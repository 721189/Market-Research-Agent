import { NextRequest, NextResponse } from "next/server";
import { verifyAuth } from "@/lib/auth";

const FASTAPI_URL = process.env.FASTAPI_URL || "http://127.0.0.1:8000";

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

    const stream = new ReadableStream({
      async start(controller) {
        let isClosed = false;
        
        req.signal.addEventListener('abort', () => {
          isClosed = true;
          try { controller.close(); } catch { /* ignore */ }
        });

        let consecutiveErrors = 0;

        const pollFastAPI = async () => {
          if (isClosed) return;
          try {
            const res = await fetch(`${FASTAPI_URL}/api/v1/research/${encodeURIComponent(task_id)}`, {
              headers: {
                "Authorization": authHeader,
                "X-Organization-ID": orgId,
                "X-User-ID": user?.uid || "",
              }
            });

            if (res.ok) {
              consecutiveErrors = 0;
              const data = await res.json();
              const payload = {
                status: data.status,
                task_id,
                progress: data.progress || 0,
                result: data.result || null,
                error: data.error_message || null,
              };
              controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(payload)}\n\n`));

              if (data.status === "COMPLETED" || data.status === "FAILED" || data.status === "CANCELLED") {
                isClosed = true;
                try { controller.close(); } catch { /* ignore */ }
                return;
              }
            } else if (res.status === 404) {
              // Task might still be initializing in Celery/DB
              consecutiveErrors++;
              if (consecutiveErrors > 10) {
                controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ status: "FAILED", task_id, error: "Research job initialization timed out." })}\n\n`));
                isClosed = true;
                try { controller.close(); } catch { /* ignore */ }
                return;
              }
              // Send keepalive ping
              controller.enqueue(new TextEncoder().encode(`: keepalive\n\n`));
            }
          } catch {
            consecutiveErrors++;
            if (consecutiveErrors > 8) {
              controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ status: "FAILED", task_id, error: "Backend connectivity interrupted." })}\n\n`));
              isClosed = true;
              try { controller.close(); } catch { /* ignore */ }
              return;
            }
            // Send heartbeat comment
            controller.enqueue(new TextEncoder().encode(`: heartbeat retry=${consecutiveErrors}\n\n`));
          }

          if (!isClosed) {
            setTimeout(pollFastAPI, 1500);
          }
        };

        pollFastAPI();
      }
    });

    return new NextResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Internal error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
