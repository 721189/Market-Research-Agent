import { NextRequest, NextResponse } from "next/server";
import { adminDb } from "../../../lib/firebase-admin";
import { verifyAuth } from "../../../lib/auth";
import { executeResearchJob } from "../../../lib/research/engine";
import { checkQuota } from "../../../lib/research/billing";

export async function POST(req: NextRequest) {
  try {
    const user = await verifyAuth(req);
    const body = await req.json();
    const { orgId, product_idea, mode, idempotencyKey } = body;

    if (!orgId || !product_idea) {
      return NextResponse.json({ error: "Missing orgId or product_idea" }, { status: 400 });
    }

    const hasQuota = await checkQuota(orgId);
    if (!hasQuota) {
      return NextResponse.json({ error: "Quota exceeded or insufficient funds." }, { status: 402 });
    }

    // Idempotency: Check if job with this idempotency key already exists for this org
    const existingJobs = await adminDb.collection("organizations").doc(orgId).collection("researchJobs")
      .where("idempotencyKey", "==", idempotencyKey || "")
      .limit(1).get();

    if (!existingJobs.empty && idempotencyKey) {
      return NextResponse.json({ task_id: existingJobs.docs[0].id });
    }

    const jobRef = adminDb.collection("organizations").doc(orgId).collection("researchJobs").doc();
    
    await jobRef.set({
      id: jobRef.id,
      organizationId: orgId,
      creatorId: user.uid,
      productIdea: product_idea,
      mode: mode || "deep",
      status: "QUEUED",
      progress: 0,
      idempotencyKey: idempotencyKey || "",
      createdAt: Date.now(),
      updatedAt: Date.now()
    });

    // Fire and forget (Worker simulation)
    executeResearchJob(jobRef.id, orgId, user.uid, product_idea, mode || "deep");

    return NextResponse.json({ task_id: jobRef.id });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
