import { adminDb } from "../firebase-admin";
import { Type, Schema } from "@google/genai";
import { calculateUnitEconomics } from "./financial";
import { logUsage } from "./billing";
import { queuePdfGeneration } from "./pdf-worker";
import { executeLLM, TaskComplexity } from "./llm";
import { calculateEvidenceDerivedConfidence, validateEvidence } from "./confidence";
import crypto from "crypto";

async function runCompetitorAnalysis(productIdea: string) {
  const schema: Schema = {
    type: Type.ARRAY,
    items: {
      type: Type.OBJECT,
      properties: {
        name: { type: Type.STRING },
        price: { type: Type.NUMBER },
        url: { type: Type.STRING },
        features: { type: Type.ARRAY, items: { type: Type.STRING } },
        marketPositioning: { type: Type.STRING },
        targetAudience: { type: Type.STRING },
        weakness: { type: Type.STRING },
      },
      required: ["name", "price", "url", "features", "marketPositioning", "targetAudience", "weakness"]
    }
  };

  const prompt = `You are an elite market intelligence researcher. Conduct an exhaustive competitive analysis for the following product idea: "${productIdea}". 
  Use the Google Search tool to find 3 to 5 real-world, highly relevant competitors. 
  For each competitor, extract:
  - Standard retail price (in USD as a number).
  - Valid website URL.
  - Top 3 distinct product features.
  - How they position themselves in the market (e.g., luxury, budget, eco-friendly).
  - Their primary target audience demographics.
  - Their most critical product or business weakness (e.g., based on reviews or missing features).`;
  
  // Intelligent model routing: "cheap" for extraction, but we use search so we need accuracy.
  const response = await executeLLM(prompt, "medium", schema, [{ googleSearch: {} }]);

  return {
    data: JSON.parse(response.text || "[]") as Array<{ 
      name: string; price: number; url: string; 
      features: string[]; marketPositioning: string; targetAudience: string; weakness: string 
    }>,
    tokens: response.tokens,
    model: response.model
  };
}

async function runFinancialExtraction(productIdea: string) {
  const schema: Schema = {
    type: Type.OBJECT,
    properties: {
      estimatedCogs: { type: Type.NUMBER, description: "Estimated Cost of Goods Sold in USD" },
      targetMargin: { type: Type.NUMBER, description: "Standard industry gross margin percentage (e.g. 60)" }
    },
    required: ["estimatedCogs", "targetMargin"]
  };

  const prompt = `As a supply chain and financial expert, estimate the unit Cost of Goods Sold (COGS) to manufacture a standard version of this product at scale: "${productIdea}". Also provide the standard industry gross margin percentage for this category.`;

  // Intelligent model routing: "medium" for analysis
  const response = await executeLLM(prompt, "medium", schema);

  return {
    data: JSON.parse(response.text || '{"estimatedCogs": 10, "targetMargin": 50}') as { estimatedCogs: number; targetMargin: number },
    tokens: response.tokens,
    model: response.model
  };
}

async function synthesizeReport(productIdea: string, competitors: any[], economics: any) {
  const prompt = `You are an elite Strategy Consultant from a top-tier management consulting firm (e.g., McKinsey, BCG). 
  Write a comprehensive, highly detailed market research report and launch brief for this product idea: "${productIdea}".
  
Here is the extracted market data and deterministic financial calculations:
Competitors: ${JSON.stringify(competitors, null, 2)}
Economics: COGS $${economics.estimatedCogs}, Suggested Retail $${economics.suggestedRetailPrice}, Margin ${economics.projectedMarginPercentage}%

Produce a sophisticated markdown document strictly formatted with the following sections:
## 1. Executive Summary & Market Overview
(Provide a high-level overview, industry trends, and the core value proposition)

## 2. Competitive Landscape & SWOT Analysis
(Provide an aggregate SWOT analysis of the market based on the competitor data provided)

## 3. Target Demographics & Go-to-Market Strategy
(Who is the buyer? How should we reach them?)

## 4. Unit Economics Breakdown
(Explain the financial viability based on the provided COGS, Retail Price, and Margin)

Do NOT invent new competitor names or financial numbers. Use only the data provided above.`;

  // Intelligent model routing: "high_quality" for final synthesis and strategy
  const response = await executeLLM(prompt, "high_quality");

  return {
    brief: response.text || "No brief generated.",
    competitors: competitors.map((c: any) => 
      `- **${c.name}** ($${c.price}): Targets ${c.targetAudience}. Positioned as ${c.marketPositioning}. Weakness: ${c.weakness} (Features: ${c.features.join(", ")})`
    ).join("\\n"),
    tokens: response.tokens,
    model: response.model
  };
}

export async function executeResearchJob(jobId: string, orgId: string, userId: string, productIdea: string, mode: string) {
  const jobRef = adminDb.collection("organizations").doc(orgId).collection("researchJobs").doc(jobId);
  const startTime = Date.now();
  
  try {
    // 0. Deduplication Check
    const normalizedQuery = productIdea.trim().toLowerCase();
    const hash = crypto.createHash('sha256').update(normalizedQuery).digest('hex');
    
    const duplicateQuery = await adminDb.collection("organizations").doc(orgId).collection("researchJobs")
      .where("queryHash", "==", hash)
      .where("status", "==", "COMPLETED")
      .orderBy("createdAt", "desc")
      .limit(1)
      .get();
      
    if (!duplicateQuery.empty) {
      const existing = duplicateQuery.docs[0].data();
      await jobRef.update({ 
        status: "COMPLETED", 
        progress: 100, 
        updatedAt: Date.now(),
        result: existing.result,
        deduplicatedFrom: existing.id
      });
      return;
    }

    await jobRef.update({ status: "RESEARCHING", progress: 10, updatedAt: Date.now(), queryHash: hash });

    // 1. Parallel Execution
    const [compRes, finRes] = await Promise.all([
      runCompetitorAnalysis(productIdea),
      runFinancialExtraction(productIdea)
    ]);
    
    const competitors = compRes.data;
    const financialInputs = finRes.data;
    let totalTokens = compRes.tokens + finRes.tokens;

    await jobRef.update({ status: "ANALYZING", progress: 50, updatedAt: Date.now() });

    // 2. Deterministic Financial Engine
    const eco = calculateUnitEconomics(financialInputs.estimatedCogs, financialInputs.targetMargin);
    
    // 3. Save evidence & claims to DB
    const batch = adminDb.batch();
    
    competitors.forEach(comp => {
      const evidence = validateEvidence(comp.url || "https://example.com", new URL(comp.url.includes("http") ? comp.url : "https://example.com").hostname);
      
      const evidenceRef = jobRef.collection("evidence").doc();
      batch.set(evidenceRef, {
        id: evidenceRef.id,
        jobId,
        url: evidence.url,
        domain: evidence.domain,
        title: `Competitor Profile: ${comp.name}`,
        retrievedAt: evidence.retrievedAt,
        authorityScore: evidence.authorityScore,
      });

      const claimRef = jobRef.collection("claims").doc();
      batch.set(claimRef, {
        id: claimRef.id,
        jobId,
        text: `${comp.name} is priced around $${comp.price} but suffers from: ${comp.weakness}`,
        confidence: evidence.authorityScore > 50 ? 95 : 75,
        sourceIds: [evidenceRef.id],
        createdAt: Date.now()
      });
    });

    await batch.commit();

    await jobRef.update({ status: "GENERATING_REPORT", progress: 75, updatedAt: Date.now() });

    // 4. Synthesis
    const finalReport = await synthesizeReport(productIdea, competitors, eco);
    totalTokens += finalReport.tokens;
    
    // Calculate Evidence-Derived Confidence
    const confidenceScore = calculateEvidenceDerivedConfidence(competitors, eco);
    
    const executionTimeMs = Date.now() - startTime;
    
    await jobRef.update({
      status: "COMPLETED",
      progress: 100,
      updatedAt: Date.now(),
      result: {
        product_idea: productIdea,
        mode,
        stage: "complete",
        financials: {
          product_name: productIdea,
          estimated_cogs: eco.estimatedCogs,
          suggested_retail_price: eco.suggestedRetailPrice,
          projected_margin_percentage: eco.projectedMarginPercentage,
          key_competitor_prices: competitors.map(c => `${c.name}: $${c.price}`)
        },
        confidence: confidenceScore,
        launch_brief: finalReport.brief,
        competitor_report: finalReport.competitors
      }
    });
    
    // Trigger Background PDF Generation
    queuePdfGeneration(jobId, orgId);

    // 5. Cost Engine & Metering
    await logUsage(orgId, userId, jobId, "research_run", {
      tokens: totalTokens,
      estimatedCost: (totalTokens / 1000) * 0.001, // Mock pricing
      executionTimeMs,
      models: ["gemini-2.5-flash", "gemini-2.5-pro"]
    });

  } catch (error: any) {
    console.error("Research Engine Error:", error);
    await jobRef.update({ status: "FAILED", error: error.message, updatedAt: Date.now() });
  }
}
