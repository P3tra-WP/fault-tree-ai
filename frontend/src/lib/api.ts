import type { AnalysisResult, Control, FaultTree, LossMagnitude, Provider } from "../types";

const BASE = "/api";

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      // response body wasn't JSON -- fall back to statusText
    }
    throw new Error(detail);
  }
  return (await resp.json()) as T;
}

function postJson<T>(url: string, body: unknown): Promise<T> {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => handle<T>(r));
}

export function createAnalysis(params: {
  provider: Provider;
  api_key: string;
  model?: string;
  top_event: string;
  threat_model_markdown: string;
}): Promise<AnalysisResult> {
  return postJson(`${BASE}/analyses`, params);
}

export function createAnalysisFromImport(fault_tree: FaultTree): Promise<AnalysisResult> {
  return postJson(`${BASE}/analyses/import`, { fault_tree });
}

export function getAnalysis(id: string): Promise<AnalysisResult> {
  return fetch(`${BASE}/analyses/${id}`).then((r) => handle<AnalysisResult>(r));
}

export function updateAnalysis(
  id: string,
  params: { fault_tree: FaultTree; controls: Control[]; loss_magnitude?: LossMagnitude | null }
): Promise<AnalysisResult> {
  return fetch(`${BASE}/analyses/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  }).then((r) => handle<AnalysisResult>(r));
}

export function importIntoAnalysis(
  id: string,
  params: { fault_tree: FaultTree; mode: "replace" | "merge"; attach_gate_id?: string | null }
): Promise<AnalysisResult> {
  return postJson(`${BASE}/analyses/${id}/import`, params);
}

export function exportUrl(id: string, format: "json" | "markdown"): string {
  return `${BASE}/analyses/${id}/export?format=${format}`;
}
