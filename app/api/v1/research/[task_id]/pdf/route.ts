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
      return new NextResponse("Missing orgId", { status: 400 });
    }

    const jobDoc = await adminDb.collection("organizations").doc(orgId).collection("researchJobs").doc(task_id).get();
    
    if (!jobDoc.exists) {
      return new NextResponse("Task not found", { status: 404 });
    }

    const task = jobDoc.data()!;
    
    if (task.status !== "COMPLETED" || !task.result) {
      return new NextResponse("Report not ready yet", { status: 409 });
    }

    if (task.pdfStatus !== "READY" || !task.pdfArtifactId) {
      return new NextResponse("PDF is still generating in the background. Please try again shortly.", { status: 202 });
    }

    // Fetch from "Object Storage" (Artifacts collection)
    const artifactDoc = await adminDb.collection("organizations").doc(orgId).collection("artifacts").doc(task.pdfArtifactId).get();
    if (!artifactDoc.exists) {
      return new NextResponse("PDF Artifact missing.", { status: 404 });
    }
    
    const artifact = artifactDoc.data()!;
    const pdfBuffer = Buffer.from(artifact.data, "base64");
    
    const product = task.result.product_idea || "Product";
    const filename = `${product.replace(/\s+/g, '_')}_report.pdf`;

    return new NextResponse(pdfBuffer, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${filename}"`
      }
    });
  } catch (error: any) {
    return new NextResponse(error.message, { status: 500 });
  }
}

