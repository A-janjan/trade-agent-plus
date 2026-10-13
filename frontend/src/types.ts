export type RunStatus = "running" | "done" | "failed";

export interface RunSummary {
    run_id: string;
    ticker: string;
    trade_date: string;
    asset_type: string;
    status: RunStatus;
    started_at: number;
    elapsed_seconds: number | null;
    error: string | null;
    rating: string | null;
    event_count: number;
}

export interface RunStartRequest {
    ticker: string;
    trade_date: string;
    asset_type?: string;
    selected_analysts?: string[];
    portfolio?: object | null;
}

// Matches tradeagents.api.events — every event has a `type` and a `ts`.
export type StreamEvent =
    | { type: "run.started"; ts: number; run_id: string; ticker: string; trade_date: string; models: Record<string, string> }
    | { type: "run.state"; ts: number; state: Record<string, unknown> }
    | { type: "run.finished"; ts: number; run_id: string; rating: string | null; elapsed_seconds: number }
    | { type: "run.failed"; ts: number; run_id: string; error: string }
    | { type: "node.finished"; ts: number; node: string }
    | { type: "token"; ts: number; node: string; text: string }
    | { type: "tool.started"; ts: number; node: string; tool: string; args: unknown }
    | { type: "tool.finished"; ts: number; node: string; tool: string }
    | { type: "report"; ts: number; key: string; content: string }
    | { type: "debate.turn"; ts: number; debate: string; speaker: string; content: string }
    | { type: "decision"; ts: number; rating: string | null; text: string; trader_text: string; investment_plan: string }
    | { type: "settled"; ts: number; entries: unknown[] };