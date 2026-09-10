"use client";

import type { PollResponse } from "./types";
import { auth } from "./firebase";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

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
      ? `${process.env.NEXT_PUBLIC_API_BASE}/api/research`
      : "/api/research";
  return jsonFetch<{ task_id: string }>(path, {
    method: "POST",
    body: JSON.stringify({ orgId, product_idea: productIdea, mode, idempotencyKey }),
  });
}

// Keeping the old poll method temporarily just in case
export async function pollResearch(orgId: string, taskId: string): Promise<PollResponse> {
  const path =
    process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.length > 0
      ? `${process.env.NEXT_PUBLIC_API_BASE}/api/research/${encodeURIComponent(taskId)}?orgId=${orgId}`
      : `/api/research/${encodeURIComponent(taskId)}?orgId=${orgId}`;
  return jsonFetch<PollResponse>(path);
}

export function researchPdfUrl(orgId: string, taskId: string): string {
  return `/api/research/${encodeURIComponent(taskId)}/pdf?orgId=${orgId}`;
}