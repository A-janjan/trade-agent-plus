import type { RunStartRequest, RunSummary } from "./types";

async function errorFromResponse(response: Response, fallback: string) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    return payload?.detail || response.statusText || fallback;
}

export async function startRun(body: RunStartRequest): Promise<RunSummary> {
    const response = await fetch("/api/runs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        throw new Error(await errorFromResponse(response, "Failed to start run"));
    }
    return response.json() as Promise<RunSummary>;
}

export async function getRun(runId: string): Promise<RunSummary & { state: unknown }> {
    const response = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
    if (!response.ok) {
        throw new Error(await errorFromResponse(response, "Run not found"));
    }
    return response.json() as Promise<RunSummary & { state: unknown }>;
}

export async function listRuns(): Promise<RunSummary[]> {
    const response = await fetch("/api/runs");
    if (!response.ok) {
        throw new Error(await errorFromResponse(response, "Could not load run history"));
    }
    return response.json() as Promise<RunSummary[]>;
}
