import type { Capabilities, ReviewRun } from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

function buildUrl(path: string): string {
  if (!API_BASE) {
    return path;
  }
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${API_BASE}${path}`;
}

export async function fetchCapabilities(): Promise<Capabilities> {
  const response = await fetch(buildUrl("/api/capabilities"));
  if (!response.ok) {
    throw new Error(`Failed to load capabilities: ${response.status}`);
  }
  return response.json();
}

export async function fetchRuns(mode = "review"): Promise<ReviewRun[]> {
  const response = await fetch(buildUrl(`/api/runs?mode=${encodeURIComponent(mode)}`));
  if (!response.ok) {
    throw new Error(`Failed to load runs: ${response.status}`);
  }
  const payload = (await response.json()) as { runs: ReviewRun[] };
  return payload.runs;
}

export async function fetchRun(runId: string): Promise<ReviewRun> {
  const response = await fetch(buildUrl(`/api/review/runs/${runId}`));
  if (!response.ok) {
    throw new Error(`Failed to load run: ${response.status}`);
  }
  return response.json();
}

export async function createReviewRun(formData: FormData): Promise<ReviewRun> {
  const response = await fetch(buildUrl("/api/review/runs"), {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail || `Failed to create run: ${response.status}`);
  }
  return response.json();
}

export function createRunEventSource(runId: string, after = 0): EventSource {
  return new EventSource(buildUrl(`/api/review/runs/${runId}/events?after=${after}`));
}

export function artifactUrl(path: string): string {
  return buildUrl(path);
}
