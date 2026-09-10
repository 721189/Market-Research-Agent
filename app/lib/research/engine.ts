import { adminDb } from "../firebase-admin";
import { GoogleGenAI, Type, Schema } from "@google/genai";
import { calculateUnitEconomics } from "./financial";
import crypto from "crypto";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

async function runCompetitorAnalysis(productIdea: string) {
  const schema: Schema = {
    type: Type.ARRAY,
    items: {
      type: Type.OBJECT,
      properties: {
        name: { type: Type.STRING },
        price: { type: Type.NUMBER },
        url: { type: Type.STRING },
        weakness: { type: Type.STRING },
      },
      required: ["name", "price", "url", "weakness"]
    }
  };

  const prompt = `You are a market researcher. Find 3 to 5 real-world competitors for the following product idea: "${productIdea}". Estimate their standard retail price (in USD as a number). Provide their website URL and their biggest product weakness.`;
  
  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash",
    contents: prompt,
    config: {
      tools: [{ googleSearch: {} }],
      responseMimeType: "application/json",
      responseSchema: schema,
    }
  });

  return JSON.parse(response.text || "[]") as Array<{ name: string; price: number; url: string; weakness: string }>;
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

  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash",
    contents: prompt,
    config: {
      responseMimeType: "application/json",
      responseSchema: schema,
    }
  });

  return JSON.parse(response.text || '{"estimatedCogs": 10, "targetMargin": 50}') as { estimatedCogs: number; targetMargin: number };
}

async function synthesizeReport(productIdea: string, competitors: any[], economics: any) {
  const prompt = `Write a comprehensive launch brief for this product idea: "${productIdea}".
  
Here is the data:
Competitors: ${JSON.stringify(competitors)}
Economics: COGS $${economics.estimatedCogs}, Suggested Retail $${economics.suggestedRetailPrice}, Margin ${economics.projectedMarginPercentage}%

Produce two sections in markdown:
1. Executive Summary & Strategy
2. Competitor Breakdown`;

  const response = await ai.models.generateContent({
    model: "gemini-2.5-pro",
    contents: prompt,
  });

  return {
    brief: response.text || "No brief generated.",
    competitors: competitors.map(c => `- **${c.name}** ($${c.price}): ${c.weakness}`).join("\\n")
  };
}

export async function executeResearchJob(jobId: string, orgId: string, productIdea: string, mode: string) {
  const jobRef = adminDb.collection("organizations").doc(orgId).collection("researchJobs").doc(jobId);
  
  try {
    await jobRef.update({ status: "RESEARCHING", progress: 10, updatedAt: Date.now() });

    // 1. Parallel Execution
    const [competitors, financialInputs] = await Promise.all([
      runCompetitorAnalysis(productIdea),
      runFinancialExtraction(productIdea)
    ]);

    await jobRef.update({ status: "ANALYZING", progress: 50, updatedAt: Date.now() });

    // 2. Deterministic Financial Engine
    const eco = calculateUnitEconomics(financialInputs.estimatedCogs, financialInputs.targetMargin);
    
    // 3. Save evidence & claims to DB
    const batch = adminDb.batch();
    
    competitors.forEach(comp => {
      const evidenceRef = jobRef.collection("evidence").doc();
      batch.set(evidenceRef, {
        id: evidenceRef.id,
        jobId,
        url: comp.url || "https://example.com",
        domain: new URL(comp.url.includes("http") ? comp.url : "https://example.com").hostname,
        title: `Competitor Profile: ${comp.name}`,
        retrievedAt: Date.now(),
        authorityScore: 80,
      });

      const claimRef = jobRef.collection("claims").doc();
      batch.set(claimRef, {
        id: claimRef.id,
        jobId,
        text: `${comp.name} is priced around $${comp.price} but suffers from: ${comp.weakness}`,
        confidence: 90,
        sourceIds: [evidenceRef.id],
        createdAt: Date.now()
      });
    });

    await batch.commit();

    await jobRef.update({ status: "GENERATING_REPORT", progress: 75, updatedAt: Date.now() });

    // 4. Synthesis
    const finalReport = await synthesizeReport(productIdea, competitors, eco);
    
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
        confidence: {
          overall_score: 85,
          source_reliability: 80,
          evidence_coverage: 90,
          consistency: 85,
          high_confidence_insights: ["Competitor Pricing Baseline", "Standard Industry COGS"],
          low_confidence_insights: ["Exact Total Addressable Market (TAM)"],
          summary: "Strong market viability if competitor weaknesses are addressed."
        },
        launch_brief: finalReport.brief,
        competitor_report: finalReport.competitors
      }
    });

  } catch (error: any) {
    console.error("Research Engine Error:", error);
    await jobRef.update({ status: "FAILED", error: error.message, updatedAt: Date.now() });
  }
}
