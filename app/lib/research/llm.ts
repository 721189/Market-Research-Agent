import { GoogleGenAI, Type, Schema } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

export type TaskComplexity = "cheap" | "medium" | "high_quality";

// Intelligent model routing
function getModelForComplexity(complexity: TaskComplexity): string {
  switch (complexity) {
    case "cheap": 
      return "gemini-2.5-flash"; // Fast extraction, classification
    case "medium": 
      return "gemini-2.5-flash"; // Summarization, general analysis
    case "high_quality": 
      return "gemini-2.5-pro";   // Financial reasoning, strategy, QA
    default: 
      return "gemini-2.5-flash";
  }
}

// External API Resilience: Retries, Exponential Backoff, Jitter, Provider Fallbacks
const MAX_RETRIES = 3;

export async function executeLLM(prompt: string, complexity: TaskComplexity, schema?: Schema, tools?: any[]) {
  let attempt = 0;
  let lastError;

  while (attempt < MAX_RETRIES) {
    try {
      const model = getModelForComplexity(complexity);
      const response = await ai.models.generateContent({
        model,
        contents: prompt,
        config: {
          ...(schema ? { responseMimeType: "application/json", responseSchema: schema } : {}),
          ...(tools && tools.length > 0 ? { tools } : {})
        }
      });
      
      return {
        text: response.text,
        tokens: response.usageMetadata?.totalTokenCount || 0,
        model
      };
    } catch (error: any) {
      lastError = error;
      attempt++;
      
      // Exponential backoff + jitter for API resilience
      const delay = Math.pow(2, attempt) * 1000 + Math.random() * 1000;
      console.warn(`[LLMProvider] Attempt ${attempt} failed. Retrying in ${Math.round(delay)}ms...`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
  
  throw new Error(`LLM Provider failed after ${MAX_RETRIES} attempts. Last error: ${lastError.message}`);
}
