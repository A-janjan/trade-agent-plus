import type { RunStartRequest, RunSummary } from "./types";

export async function startRun(body: RunStartRequest): Promise<RunSummary> {
  const res = await fetch("/api/runs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? `Failed to start run`);
  }
  return res.json();
}

export async function getRun(runId: string): Promise<RunSummary & { state: unknown }> {
  const res = await fetch(`/api/runs/${runId}`);
  if (!res.ok) throw new Error("Run not found");
  return res.json();
}

export async function listRuns(): Promise<RunSummary[]> {
  const res = await fetch("/api/runs");
  return res.json();
}