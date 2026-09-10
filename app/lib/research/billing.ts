import { adminDb } from "../firebase-admin";

export async function checkQuota(orgId: string): Promise<boolean> {
  const orgDoc = await adminDb.collection("organizations").doc(orgId).get();
  if (!orgDoc.exists) return false;
  
  const orgData = orgDoc.data()!;
  
  // Default Free Plan Limits (Daily: 5 researches)
  const plan = orgData.plan || "free";
  const limits: Record<string, number> = {
    "free": 5,
    "pro": 100,
    "enterprise": 1000
  };
  
  const dailyLimit = limits[plan] || 5;

  const today = new Date();
  today.setHours(0,0,0,0);
  
  const usageQuery = await adminDb.collection("organizations").doc(orgId).collection("usage")
    .where("type", "==", "research_run")
    .where("timestamp", ">=", today.getTime())
    .count().get();
    
  return usageQuery.data().count < dailyLimit;
}

export async function logUsage(orgId: string, userId: string, jobId: string, type: string, metadata: any) {
  const usageRef = adminDb.collection("organizations").doc(orgId).collection("usage").doc();
  await usageRef.set({
    id: usageRef.id,
    jobId,
    userId,
    type, // 'research_run', 'llm_call', 'pdf_export'
    metadata,
    timestamp: Date.now()
  });
}

export async function logAudit(orgId: string, userId: string, action: string, resource: string, context: any) {
  const auditRef = adminDb.collection("auditEvents").doc();
  await auditRef.set({
    id: auditRef.id,
    organizationId: orgId,
    userId,
    action,
    resource,
    context,
    timestamp: Date.now()
  });
}
