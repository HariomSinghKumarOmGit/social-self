import type { Post, ReviewStats } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error((data as { error?: string }).error || `Request failed (${res.status})`);
  }
  return data as T;
}

export async function fetchQueue(params: {
  platform?: string;
  author?: string;
  sort?: string;
}): Promise<{ posts: Post[]; stats: ReviewStats }> {
  const q = new URLSearchParams();
  if (params.platform) q.set("platform", params.platform);
  if (params.author) q.set("author", params.author);
  if (params.sort) q.set("sort", params.sort);
  return request(`/api/review/queue?${q.toString()}`);
}

export async function fetchSourceAccounts(): Promise<Record<string, string[]>> {
  return request("/api/source-accounts");
}

export async function fetchApproved(): Promise<Post[]> {
  return request("/api/scheduled");
}

export async function approvePost(postId: number): Promise<void> {
  await request("/api/review/approve", {
    method: "POST",
    body: JSON.stringify({ post_id: postId }),
  });
}

export async function rejectPost(postId: number): Promise<void> {
  await request("/api/review/reject", {
    method: "POST",
    body: JSON.stringify({ post_id: postId }),
  });
}

export async function triggerScrape(): Promise<void> {
  await request("/api/scrape", { method: "POST" });
}
