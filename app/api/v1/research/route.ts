import { NextRequest, NextResponse } from "next/server";
import { verifyAuth } from "@/lib/auth";
import { createTask, updateTask, listTasks } from "@/lib/tasksStore";

function runLocalSimulation(taskId: string, productIdea: string) {
  setTimeout(() => {
    updateTask(taskId, { progress: 35 });
  }, 1000);

  setTimeout(() => {
    updateTask(taskId, { progress: 70 });
  }, 2200);

  setTimeout(() => {
    updateTask(taskId, {
      progress: 100,
      status: "COMPLETED",
      result: {
        product_idea: productIdea,
        financials: {
          estimated_cogs: 14.50,
          suggested_retail_price: 49.99,
          projected_margin_percentage: 71.0,
          key_competitor_prices: ["$45.00 (Competitor A)", "$59.99 (Competitor B)", "$39.00 (Competitor C)"],
          pricing_basis: productIdea
        },
        confidence: {
          overall_score: 89,
          source_reliability: 92,
          evidence_coverage: 85,
          consistency: 90,
          summary: "High market viability with strong unit economics and favorable margin profile."
        },
        executive_summary: `# Launch Brief: ${productIdea}\n\n## 1. Market Opportunity\nThere is robust consumer demand for **${productIdea}**. Competitor analysis indicates an underserved mid-premium tier with 71% projected gross margins.\n\n## 2. Unit Economics\n- **Estimated COGS**: $14.50\n- **Target Retail Price**: $49.99\n- **Gross Margin**: 71.0%\n\n## 3. Recommended Go-To-Market\n- Focus direct-to-consumer digital acquisition via targeted social proof and influencer partnerships.\n- Emphasize superior build quality and user experience.`
      }
    });
  }, 3500);
}

export async function GET(req: NextRequest) {
  try {
    await verifyAuth(req);
    const tasks = listTasks();
    return NextResponse.json({ tasks });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    await verifyAuth(req);
    const body = await req.json();
    const orgId = body.orgId || body.org_id;
    const product_idea = body.product_idea || body.product;
    const mode = body.mode || "deep";

    if (!orgId || !product_idea) {
      return NextResponse.json({ error: "Missing orgId or product_idea" }, { status: 400 });
    }

    // Instantly create task in local store and start simulation
    const taskId = createTask(product_idea, mode);
    runLocalSimulation(taskId, product_idea);

    return NextResponse.json({ task_id: taskId, status: "RUNNING" }, { status: 202 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
