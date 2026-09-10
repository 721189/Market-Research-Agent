import { NextRequest, NextResponse } from "next/server";
import { adminDb } from "../../../../lib/firebase-admin";
import { verifyAuth } from "../../../../lib/auth";
import PDFDocument from "pdfkit";
import { PassThrough } from "stream";

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

  const data = task.result;
  const product = data.financials?.product_name || data.product_idea || "Product";
  const summary = data.confidence?.summary || "No summary available";
  const brief = data.launch_brief || "";
  const competitor_report = data.competitor_report || "";
  const cogs = data.financials?.estimated_cogs || 0;
  const retail = data.financials?.suggested_retail_price || 0;
  const margin = data.financials?.projected_margin_percentage || 0;

  // Create a PDFDocument
  const doc = new PDFDocument({ margin: 50 });
  
  const chunks: Buffer[] = [];
  doc.on("data", (chunk) => chunks.push(chunk));
  
  const endPromise = new Promise<Buffer>((resolve) => {
    doc.on("end", () => resolve(Buffer.concat(chunks)));
  });

  // Build the PDF
  doc.fontSize(24).text(`${product} - Market Research`, { align: 'center' });
  doc.moveDown();
  
  doc.fontSize(16).text('Executive Summary');
  doc.fontSize(12).text(summary);
  doc.moveDown();

  doc.fontSize(16).text('Financial Margin');
  doc.fontSize(12).text(`Estimated COGS: $${cogs.toFixed(2)}`);
  doc.fontSize(12).text(`Suggested Retail Price: $${retail.toFixed(2)}`);
  doc.fontSize(12).text(`Projected Margin: ${margin.toFixed(1)}%`);
  doc.moveDown();
  
  if (data.financials?.key_competitor_prices?.length > 0) {
    doc.fontSize(14).text('Key Competitor Prices');
    data.financials.key_competitor_prices.forEach((c: string) => {
      doc.fontSize(12).text(`- ${c}`);
    });
    doc.moveDown();
  }

  doc.fontSize(16).text('Launch Brief');
  doc.fontSize(12).text(brief);
  doc.moveDown();
  
  doc.fontSize(16).text('Competitor Report');
  doc.fontSize(12).text(competitor_report);

  doc.end();

  const pdfBuffer = await endPromise;

  const filename = `${product.replace(/\s+/g, '_')}_report.pdf`;
  
  return new NextResponse(pdfBuffer as any, {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="${filename}"`
    }
  });
  } catch (error: any) {
    return new NextResponse(error.message, { status: 500 });
  }
}
