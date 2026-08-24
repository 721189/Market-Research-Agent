"use client";

import type { PollResponse } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
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
  productIdea: string,
  mode: "quick" | "deep" | "batch"
): Promise<{ task_id: string }> {
  const path =
    process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.length > 0
      ? `${process.env.NEXT_PUBLIC_API_BASE}/api/research`
      : "/api/research";
  return jsonFetch<{ task_id: string }>(path, {
    method: "POST",
    body: JSON.stringify({ product_idea: productIdea, mode }),
  });
}

export async function pollResearch(taskId: string): Promise<PollResponse> {
  const path =
    process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.length > 0
      ? `${process.env.NEXT_PUBLIC_API_BASE}/api/research/${encodeURIComponent(taskId)}`
      : `/api/research/${encodeURIComponent(taskId)}`;
  return jsonFetch<PollResponse>(path);
}

export function researchPdfUrl(taskId: string): string {
  return `/api/research/${encodeURIComponent(taskId)}/pdf`;
}