import type {
  AppRun,
  Capabilities,
  DiagnosticsPayload,
  ReviewConversation,
  ReviewConversationAction,
  ReviewConversationSummary,
  ReviewPreset,
} from "../types";

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

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(payload.detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function postForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "POST",
    body: formData,
  });
  return readJson<T>(response);
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(buildUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return readJson<T>(response);
}

export function getApiBase(): string {
  return API_BASE || window.location.origin;
}

export async function fetchCapabilities(): Promise<Capabilities> {
  const response = await fetch(buildUrl("/api/capabilities"));
  return readJson<Capabilities>(response);
}

export async function fetchRuns(mode?: string): Promise<AppRun[]> {
  const suffix = mode ? `?mode=${encodeURIComponent(mode)}` : "";
  const response = await fetch(buildUrl(`/api/runs${suffix}`));
  const payload = await readJson<{ runs: AppRun[] }>(response);
  return payload.runs;
}

export async function fetchRun(runId: string): Promise<AppRun> {
  const response = await fetch(buildUrl(`/api/runs/${runId}`));
  return readJson<AppRun>(response);
}

export async function fetchReviewPresets(): Promise<ReviewPreset[]> {
  const response = await fetch(buildUrl("/api/review/presets"));
  const payload = await readJson<{ presets: ReviewPreset[] }>(response);
  return payload.presets;
}

export async function fetchReviewConversations(): Promise<ReviewConversationSummary[]> {
  const response = await fetch(buildUrl("/api/review/conversations"));
  const payload = await readJson<{ conversations: ReviewConversationSummary[] }>(response);
  return payload.conversations;
}

export async function fetchReviewConversation(conversationId: string): Promise<ReviewConversation> {
  const response = await fetch(buildUrl(`/api/review/conversations/${conversationId}`));
  return readJson<ReviewConversation>(response);
}

export async function fetchRunDiagnostics(runId: string): Promise<DiagnosticsPayload> {
  const response = await fetch(buildUrl(`/api/review/runs/${runId}/diagnostics`));
  return readJson<DiagnosticsPayload>(response);
}

export async function createReviewRun(formData: FormData): Promise<AppRun> {
  return postForm<AppRun>("/api/review/runs", formData);
}

export async function createReviewConversation(formData: FormData): Promise<ReviewConversation> {
  return postForm<ReviewConversation>("/api/review/conversations", formData);
}

export async function createReviewConversationMessage(
  conversationId: string,
  payload: {
    mode: "chat" | "apply";
    content: string;
    base_source: "latest" | "original" | "run";
    base_run_id?: string;
    options_patch?: Record<string, unknown>;
  },
): Promise<ReviewConversationAction> {
  return postJson<ReviewConversationAction>(`/api/review/conversations/${conversationId}/messages`, payload);
}

export async function createReportRun(formData: FormData): Promise<AppRun> {
  return postForm<AppRun>("/api/report/runs", formData);
}

export async function createReportCompleteRun(formData: FormData): Promise<AppRun> {
  return postForm<AppRun>("/api/report-complete/runs", formData);
}

export async function createReportIntegrateRun(formData: FormData): Promise<AppRun> {
  return postForm<AppRun>("/api/report-integrate/runs", formData);
}

export function createRunEventSource(runId: string, after = 0): EventSource {
  return new EventSource(buildUrl(`/api/runs/${runId}/events?after=${after}`));
}

export function artifactUrl(path: string): string {
  return buildUrl(path);
}
