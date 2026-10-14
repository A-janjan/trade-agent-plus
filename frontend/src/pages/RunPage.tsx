import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import DecisionCard from "../components/DecisionCard";
import Icon from "../components/Icon";
import PipelineGraph from "../components/PipelineGraph";
import ReportPanel from "../components/ReportPanel";
import TokenPreview from "../components/TokenPreview";
import { useRunStream } from "../hooks/useRunStream";
import type { RunStatus, StreamEvent } from "../types";

const DEFAULT_ANALYSTS = ["market", "social", "news", "fundamentals"];
const ANALYST_NAMES: Record<string, string> = {
    market: "Market Analyst",
    social: "Sentiment Analyst",
    news: "News Analyst",
    fundamentals: "Fundamentals Analyst",
};
const REPORT_KEYS = [
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
    "investment_plan",
    "trader_investment_plan",
    "final_trade_decision",
];
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

interface DebateTurn {
    debate: string;
    speaker: string;
    content: string;
}

export default function RunPage() {
    const { runId } = useParams<{ runId: string }>();
    const { events, connected, done, streamError } = useRunStream(runId ?? null);
    const derived = useMemo(() => derive(events), [events]);

    const statusLabel = connected ? "Live stream" : done ? "Stream closed" : streamError ?? "Connecting…";
    const progressPercent = derived.totalStages ? Math.round((derived.finishedNodes.size / derived.totalStages) * 100) : 0;

    return (
        <div className="app-page run-page">
            <header className="topbar shell">
                <Link className="brand" to="/" aria-label="Back to tradeagents home">
                    <span className="brand-mark"><Icon name="spark" size={17} /></span>
                    <span>trade<span>agents</span></span>
                </Link>
                <div className="run-breadcrumb"><span>Workspace</span><Icon name="chevronRight" size={14} /><strong>{derived.ticker || "New run"}</strong></div>
                <div className={`topbar-run-status ${connected ? "is-live" : done ? "is-done" : ""}`}><span /> {statusLabel}</div>
            </header>

            <main className="shell run-main">
                <section className="run-hero">
                    <div>
                        <div className="eyebrow"><Icon name="activity" size={14} /> Live research run <span className="run-id-label">#{runId}</span></div>
                        <h1>{derived.ticker || "Preparing analysis"} <span>research run</span></h1>
                        <p>{derived.tradeDate ? formatDate(derived.tradeDate) : "Connecting to the research room"} <span className="hero-separator">·</span> {derived.selectedAnalysts.length} research lenses <span className="hero-separator">·</span> {derived.currentPhase}</p>
                    </div>
                    <div className="run-hero-stats">
                        <div className="run-stat"><span>Pipeline</span><strong>{progressPercent}%</strong><small>{derived.finishedNodes.size}/{derived.totalStages} nodes</small></div>
                        <div className="run-stat"><span>Events</span><strong>{events.length}</strong><small>captured live</small></div>
                    </div>
                </section>

                {streamError && !done && <div className="stream-warning" role="status"><Icon name="refresh" size={16} /><span>{streamError}</span></div>}
                {derived.failure && <div className="stream-warning stream-warning-error" role="alert"><Icon name="alert" size={16} /><span>{derived.failure}</span></div>}

                <div className="run-layout">
                    <aside className="run-sidebar">
                        <PipelineGraph
                            selectedAnalysts={derived.selectedAnalysts}
                            finished={derived.finishedNodes}
                            current={derived.currentNode}
                            status={derived.status}
                        />
                        <div className="run-context panel">
                            <div className="eyebrow"><Icon name="database" size={14} /> Run context</div>
                            <dl>
                                <div><dt>Instrument</dt><dd>{derived.ticker || "—"}</dd></div>
                                <div><dt>Analysis date</dt><dd>{derived.tradeDate || "—"}</dd></div>
                                <div><dt>Asset type</dt><dd>Equity / market</dd></div>
                            </dl>
                            <Link className="secondary-button secondary-button-full" to="/"><Icon name="plus" size={15} /> New research run</Link>
                        </div>
                    </aside>

                    <section className="run-content">
                        <DecisionCard
                            rating={derived.rating}
                            text={derived.decisionText}
                            elapsed={derived.elapsed}
                            status={derived.status}
                            eventCount={events.length}
                            error={derived.failure}
                        />
                        <TokenPreview text={derived.liveText} node={derived.currentNode} />
                        <DebateColumns turns={derived.debateTurns} />
                        <ReportPanel reports={derived.reports} />
                    </section>
                </div>
            </main>
        </div>
    );
}

function formatDate(value: string) {
    const parsed = new Date(`${value}T12:00:00`);
    return Number.isNaN(parsed.getTime())
        ? value
        : parsed.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
}

function derive(events: StreamEvent[]) {
    const finishedNodes = new Set<string>();
    const reports: Record<string, string> = {};
    const debateTurns: DebateTurn[] = [];
    const liveTextByNode: Record<string, string> = {};
    let selectedAnalysts = [...DEFAULT_ANALYSTS];
    let ticker = "";
    let tradeDate = "";
    let currentNode: string | null = null;
    let rating: string | null = null;
    let decisionText = "";
    let elapsed: number | null = null;
    let failure: string | null = null;
    let status: RunStatus = "running";

    for (const event of events) {
        switch (event.type) {
            case "run.started":
                ticker = event.ticker;
                tradeDate = event.trade_date;
                if (event.selected_analysts) selectedAnalysts = event.selected_analysts;
                break;
            case "token":
                liveTextByNode[event.node] = (liveTextByNode[event.node] ?? "") + event.text;
                currentNode = event.node;
                break;
            case "node.finished":
                finishedNodes.add(event.node);
                if (currentNode === event.node) currentNode = null;
                break;
            case "report":
                reports[event.key] = event.content;
                break;
            case "debate.turn":
                debateTurns.push({ debate: event.debate, speaker: event.speaker, content: event.content });
                break;
            case "decision":
                rating = event.rating;
                decisionText = event.text;
                break;
            case "run.state": {
                const state = event.state;
                if (!rating && typeof state.final_rating === "string") rating = state.final_rating;
                if (!decisionText && typeof state.final_trade_decision === "string") decisionText = state.final_trade_decision;
                for (const key of REPORT_KEYS) {
                    if (!reports[key] && typeof state[key] === "string") reports[key] = state[key] as string;
                }
                break;
            }
            case "run.finished":
                rating = event.rating ?? rating;
                elapsed = event.elapsed_seconds;
                status = "done";
                break;
            case "run.failed":
                failure = event.error;
                status = "failed";
                break;
            default:
                break;
        }
    }

    const currentLive = currentNode ? liveTextByNode[currentNode] ?? "" : "";
    const postStages = 8;
    const totalStages = selectedAnalysts.length + postStages;
    const currentPhase = phaseForNode(currentNode);

    return {
        selectedAnalysts,
        finishedNodes,
        totalStages,
        currentNode,
        currentPhase,
        reports,
        debateTurns,
        liveText: currentLive.slice(-2400),
        rating,
        decisionText,
        elapsed,
        failure,
        status,
        ticker,
        tradeDate,
    };
}

function phaseForNode(node: string | null) {
    if (!node) return "waiting for next stage";
    if (Object.values(ANALYST_NAMES).includes(node)) return "analyst team";
    if (["Upside Case", "Downside Case", "Investment Lead"].includes(node)) return "research debate";
    if (["Growth Advocate", "Capital Steward", "Balanced Reviewer", "Portfolio Manager"].includes(node)) return "risk debate";
    return "action plan";
}

function DebateColumns({ turns }: { turns: DebateTurn[] }) {
    if (turns.length === 0) return null;
    const byDebate: Record<string, DebateTurn[]> = {};
    for (const turn of turns) (byDebate[turn.debate] ??= []).push(turn);

    return (
        <section className="debates-section" aria-labelledby="debates-title">
            <div className="content-heading">
                <div>
                    <div className="eyebrow"><Icon name="shield" size={14} /> Adversarial review</div>
                    <h2 id="debates-title">The room challenges itself</h2>
                </div>
                <span className="report-count">{turns.length} turns</span>
            </div>
            <div className="debate-grid">
                {Object.entries(byDebate).map(([debate, list]) => (
                    <article className="debate-card panel" key={debate}>
                        <div className="debate-card-header">
                            <span className="debate-icon"><Icon name={debate === "risk_debate" ? "shield" : "spark"} size={16} /></span>
                            <div><strong>{DEBATE_LABEL[debate] ?? debate}</strong><small>Transcript · {list.length} contributions</small></div>
                        </div>
                        <div className="debate-turns">
                            {list.map((turn, index) => (
                                <div className="debate-turn" key={`${turn.speaker}-${index}`}>
                                    <div className="debate-turn-meta"><span className="turn-number">0{index + 1}</span><strong>{SPEAKER_LABEL[turn.speaker] ?? turn.speaker}</strong></div>
                                    <p>{turn.content}</p>
                                </div>
                            ))}
                        </div>
                    </article>
                ))}
            </div>
        </section>
    );
}
