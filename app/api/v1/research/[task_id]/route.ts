import { NextRequest, NextResponse } from "next/server";
import { adminDb } from "../../../../lib/firebase-admin";
import { verifyAuth } from "../../../../lib/auth";

export async function GET(req: NextRequest, { params }: { params: Promise<{ task_id: string }> }) {
  try {
    const user = await verifyAuth(req);
    const { task_id } = await params;
    
    // We need the orgId to query properly
    const { searchParams } = new URL(req.url);
    const orgId = searchParams.get("orgId");
    
    if (!orgId) {
      return NextResponse.json({ status: "FAILURE", task_id, error: "Missing orgId" }, { status: 400 });
    }

    const jobDoc = await adminDb.collection("organizations").doc(orgId).collection("researchJobs").doc(task_id).get();
    
    if (!jobDoc.exists) {
      return NextResponse.json({ status: "FAILURE", task_id, error: "Task not found" });
    }

    const task = jobDoc.data()!;
    
    return NextResponse.json({
      status: task.status,
      task_id: task_id,
      result: task.result || null,
      error: task.error || null,
    });
  } catch (error: any) {
    return NextResponse.json({ status: "FAILURE", error: error.message }, { status: 500 });
  }
}
