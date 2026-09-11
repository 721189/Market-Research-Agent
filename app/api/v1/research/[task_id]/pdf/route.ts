import { NextRequest, NextResponse } from "next/server";
import { verifyAuth } from "@/app/lib/auth";

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

    try {
      const fastApiResponse = await fetch(`${FASTAPI_URL}/api/v1/research/${encodeURIComponent(task_id)}`, {
        headers: {
          "Authorization": authHeader,
          "X-Organization-ID": orgId,
          "X-User-ID": user?.uid || "",
        },
      });

      if (fastApiResponse.ok) {
        const data = await fastApiResponse.json();
        if (data.pdf_download_url) {
          return NextResponse.redirect(data.pdf_download_url);
        }
        if (data.status !== "COMPLETED") {
          return new NextResponse("Report still generating in background", { status: 202 });
        }
      }
    } catch (e: unknown) {
      console.warn("FastAPI unreachable for PDF download redirect:", e);
    }

    return new NextResponse("Report is being prepared. Please retry shortly.", { status: 202 });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Internal error";
    return new NextResponse(message, { status: 500 });
  }
}
