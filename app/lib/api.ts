"use client";

import type { PollResponse } from "./types";
import { auth } from "./firebase";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await auth.currentUser?.getIdToken();
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Request failed with status ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function startResearch(
  orgId: string,
  productIdea: string,
  mode: "quick" | "deep" | "batch",
  idempotencyKey?: string
): Promise<{ task_id: string }> {
  const path =
    process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.length > 0
      ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/research`
      : "/api/v1/research";
  return jsonFetch<{ task_id: string }>(path, {
    method: "POST",
    body: JSON.stringify({ orgId, product_idea: productIdea, mode, idempotencyKey }),
  });
}

// Keeping the old poll method temporarily just in case
export async function pollResearch(orgId: string, taskId: string): Promise<PollResponse> {
  const path =
    process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.length > 0
      ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/research/${encodeURIComponent(taskId)}?orgId=${orgId}`
      : `/api/v1/research/${encodeURIComponent(taskId)}?orgId=${orgId}`;
  return jsonFetch<PollResponse>(path);
}

export function researchPdfUrl(orgId: string, taskId: string): string {
  return `/api/v1/research/${encodeURIComponent(taskId)}/pdf?orgId=${orgId}`;
}

export async function fetchMarketplaceTemplates() {
  const path = process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/marketplace/templates` : "/api/v1/marketplace/templates";
  return jsonFetch<Array<{ id: string; title: string; description: string; category: string; mode: string; prompt_template: string }>>(path);
}

export async function fetchScheduledResearch() {
  const path = process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/marketplace/schedules` : "/api/v1/marketplace/schedules";
  return jsonFetch<Array<{ id: string; product_idea: string; mode: string; cron_schedule: string; is_active: boolean; next_run_at: string | null }>>(path);
}

export async function createScheduledResearch(productIdea: string, cronSchedule: string, mode: string) {
  const path = process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/marketplace/schedules?product_idea=${encodeURIComponent(productIdea)}&cron_schedule=${encodeURIComponent(cronSchedule)}&mode=${encodeURIComponent(mode)}` : `/api/v1/marketplace/schedules?product_idea=${encodeURIComponent(productIdea)}&cron_schedule=${encodeURIComponent(cronSchedule)}&mode=${encodeURIComponent(mode)}`;
  return jsonFetch<{ id: string; status: string }>(path, { method: "POST" });
}

export async function fetchMarketAlerts() {
  const path = process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/marketplace/alerts` : "/api/v1/marketplace/alerts";
  return jsonFetch<Array<{ id: string; product_idea: string; alert_type: string; severity: string; headline: string; is_read: boolean; created_at: string }>>(path);
}

export async function fetchApiKeys() {
  const path = process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/apikeys` : "/api/v1/apikeys";
  return jsonFetch<Array<{ id: string; name: string; key_prefix: string; role: string; is_revoked: boolean; created_at: string }>>(path);
}

export async function createApiKey(name: string, role: string = "member") {
  const path = process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/apikeys` : "/api/v1/apikeys";
  return jsonFetch<{ id: string; name: string; secret_key: string; key_prefix: string }>(path, {
    method: "POST",
    body: JSON.stringify({ name, role }),
  });
}

export async function revokeApiKey(keyId: string) {
  const path = process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/apikeys/${encodeURIComponent(keyId)}` : `/api/v1/apikeys/${encodeURIComponent(keyId)}`;
  return jsonFetch<{ message: string }>(path, { method: "DELETE" });
}