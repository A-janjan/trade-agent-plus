import { useMemo } from "react";
import { useParams } from "react-router-dom";
import DecisionCard from "../components/DecisionCard";
import PipelineGraph from "../components/PipelineGraph";
import ReportPanel from "../components/ReportPanel";
import TokenPreview from "../components/TokenPreview";
import { useRunStream } from "../hooks/useRunStream";
import type { StreamEvent } from "../types";

const DEBATE_LABEL: Record<string, string> = {
    research_debate: "Research debate",
    risk_debate: "Risk debate",
};

const SPEAKER_LABEL: Record<string, string> = {
    upside: "Upside Case",
    downside: "Downside Case",
    growth: "Growth Advocate",
    capital: "Capital Steward",
    balanced: "Balanced Reviewer",
};

export default function RunPage() {
    const { runId } = useParams<{ runId: string }>();
    const { events, connected, done } = useRunStream(runId ?? null);

    const derived = useMemo(() => derive(events), [events]);

    return (
        <div className="min-h-screen grid grid-cols-[280px_1fr] gap-6 p-6">
            <aside className="space-y-4">
                <div>
                    <div className="text-xs uppercase tracking-wide text-slate-500">Run</div>
                    <div className="font-mono text-sm">{runId}</div>
                    <div className={connected ? "text-xs text-accent" : "text-xs text-slate-500"}>
                        {connected ? "live" : done ? "closed" : "connecting…"}
                    </div>
                </div>
                <PipelineGraph
                    selectedAnalysts={derived.selectedAnalysts}
                    finished={derived.finishedNodes}
                    current={derived.currentNode}
                />
            </aside>

            <main className="space-y-6 overflow-hidden">
                <DecisionCard
                    rating={derived.rating}
                    text={derived.decisionText}
                    elapsed={derived.elapsed}
                />
                <TokenPreview text={derived.liveText} node={derived.currentNode} />
                <DebateColumns turns={derived.debateTurns} />
                <ReportPanel reports={derived.reports} />
            </main>
        </div>
    );
}

// ---- derivations ------------------------------------------------------

function derive(events: StreamEvent[]) {
    const finishedNodes = new Set<string>();
    const reports: Record<string, string> = {};
    const debateTurns: { debate: string; speaker: string; content: string }[] = [];
    const liveTextByNode: Record<string, string> = {};
    let selectedAnalysts: string[] = [];
    let currentNode: string | null = null;
    let rating: string | null = null;
    let decisionText = "";
    let elapsed: number | null = null;

    for (const e of events) {
        switch (e.type) {
            case "run.started":
                // Infer analyst list from the first node names we see; more robust to
                // change than threading it through the run.started payload.
                break;
            case "token":
                liveTextByNode[e.node] = (liveTextByNode[e.node] ?? "") + e.text;
                currentNode = e.node;
                break;
            case "node.finished":
                finishedNodes.add(e.node);
                if (currentNode === e.node) currentNode = null;
                // Track analyst selection as we see analyst nodes finish.
                if (ANALYST_SET.has(e.node) && !selectedAnalysts.includes(e.node)) {
                    selectedAnalysts.push(e.node);
                }
                break;
            case "report":
                reports[e.key] = e.content;
                break;
            case "debate.turn":
                debateTurns.push({ debate: e.debate, speaker: e.speaker, content: e.content });
                break;
            case "decision":
                rating = e.rating;
                decisionText = e.text;
                break;
            case "run.finished":
                rating = e.rating;
                elapsed = e.elapsed_seconds;
                break;
        }
    }

    // Map analyst node names back to their selection keys.
    const analystKeys = selectedAnalysts
        .map((n) => NODE_TO_KEY[n])
        .filter((k): k is string => Boolean(k));

    const currentLive = currentNode ? liveTextByNode[currentNode] ?? "" : "";

    return {
        selectedAnalysts: analystKeys,
        finishedNodes,
        currentNode,
        reports,
        debateTurns,
        liveText: currentLive.slice(-2000),
        rating,
        decisionText,
        elapsed,
    };
}

const NODE_TO_KEY: Record<string, string> = {
    "Market Analyst": "market",
    "Sentiment Analyst": "social",
    "News Analyst": "news",
    "Fundamentals Analyst": "fundamentals",
};
const ANALYST_SET = new Set(Object.keys(NODE_TO_KEY));

function DebateColumns({ turns }: { turns: { debate: string; speaker: string; content: string }[] }) {
    if (turns.length === 0) return null;
    const byDebate: Record<string, typeof turns> = {};
    for (const t of turns) (byDebate[t.debate] ??= []).push(t);
    return (
        <div className="space-y-4">
            {Object.entries(byDebate).map(([debate, list]) => (
                <div key={debate} className="rounded border border-line bg-panel">
                    <div className="border-b border-line px-4 py-2 text-sm font-semibold">
                        {DEBATE_LABEL[debate] ?? debate}
                    </div>
                    <div className="p-4 space-y-3 max-h-96 overflow-y-auto scrollbar-thin">
                        {list.map((t, i) => (
                            <div key={i} className="text-sm">
                                <div className="text-xs font-medium text-accent mb-1">
                                    {SPEAKER_LABEL[t.speaker] ?? t.speaker}
                                </div>
                                <div className="whitespace-pre-wrap text-slate-300">{t.content}</div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}