import { NextRequest, NextResponse } from "next/server";
import { adminDb } from "../../../../../lib/firebase-admin";
import { verifyAuth } from "../../../../../lib/auth";

export async function GET(req: NextRequest, { params }: { params: Promise<{ task_id: string }> }) {
  try {
    const user = await verifyAuth(req);
    const { task_id } = await params;
    
    const { searchParams } = new URL(req.url);
    const orgId = searchParams.get("orgId");
    
    if (!orgId) {
      return NextResponse.json({ error: "Missing orgId" }, { status: 400 });
    }

    const docRef = adminDb.collection("organizations").doc(orgId).collection("researchJobs").doc(task_id);

    const stream = new ReadableStream({
      start(controller) {
        const unsubscribe = docRef.onSnapshot((docSnapshot) => {
          if (!docSnapshot.exists) {
            controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ status: "FAILURE", error: "Task not found" })}\n\n`));
            controller.close();
            unsubscribe();
            return;
          }

          const data = docSnapshot.data()!;
          const payload = {
            status: data.status,
            task_id: task_id,
            progress: data.progress || 0,
            result: data.result || null,
            error: data.error || null,
          };

          controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(payload)}\n\n`));

          if (data.status === "COMPLETED" || data.status === "FAILED" || data.status === "CANCELLED") {
            controller.close();
            unsubscribe();
          }
        }, (error) => {
          controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ status: "FAILURE", error: error.message })}\n\n`));
          controller.close();
        });

        // Close when the client disconnects
        req.signal.addEventListener('abort', () => {
          unsubscribe();
          controller.close();
        });
      }
    });

    return new NextResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
