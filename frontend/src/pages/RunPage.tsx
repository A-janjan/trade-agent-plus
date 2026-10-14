import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import DecisionCard from "../components/DecisionCard";
import Icon from "../components/Icon";
import MarkdownContent from "../components/MarkdownContent";
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
const TOOL_NODE_TO_STAGE: Record<string, string> = {
    tools_market: "Market Analyst",
    tools_news: "News Analyst",
    tools_fundamentals: "Fundamentals Analyst",
};
const POST_STAGE_NAMES = [
    "Upside Case",
    "Downside Case",
    "Investment Lead",
    "Trader",
    "Growth Advocate",
    "Capital Steward",
    "Balanced Reviewer",
    "Portfolio Manager",
];
const REPORT_KEYS = [
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
    "investment_plan",
    "trader_investment_plan",
    "final_trade_decision",
];
const REPORT_NODE_BY_KEY: Record<string, string> = {
    market_report: "Market Analyst",
    sentiment_report: "Sentiment Analyst",
    news_report: "News Analyst",
    fundamentals_report: "Fundamentals Analyst",
    investment_plan: "Investment Lead",
    trader_investment_plan: "Trader",
    final_trade_decision: "Portfolio Manager",
};
const SPEAKER_NODE_BY_KEY: Record<string, string> = {
    upside: "Upside Case",
    downside: "Downside Case",
    growth: "Growth Advocate",
    capital: "Capital Steward",
    balanced: "Balanced Reviewer",
};
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
    const progressPercent = derived.totalStages
        ? Math.min(100, Math.round((derived.completedStageCount / derived.totalStages) * 100))
        : 0;
    const evidenceCount = derived.reportCount + derived.debateTurns.length;

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
                        <div className="run-stat"><span>Stages</span><strong>{derived.completedStageCount}/{derived.totalStages}</strong><small>{progressPercent}% complete</small></div>
                        <div className="run-stat"><span>Evidence</span><strong>{derived.reportCount}</strong><small>{derived.debateTurns.length} debate turns</small></div>
                    </div>
                </section>

                {streamError && !done && <div className="stream-warning" role="status"><Icon name="refresh" size={16} /><span>{streamError}</span></div>}
                {derived.failure && <div className="stream-warning stream-warning-error" role="alert"><Icon name="alert" size={16} /><span>{derived.failure}</span></div>}

                <div className={`run-activity-strip activity-${derived.status}`}>
                    <span className="activity-icon"><Icon name="pulse" size={17} /></span>
                    <div className="activity-copy">
                        <strong>{connected ? "Analysis streaming live" : done ? "Analysis complete" : derived.status === "failed" ? "Analysis stopped" : "Preparing the research room"}</strong>
                        <small>{derived.currentNode ?? "Waiting for the next stage"} <span>·</span> {derived.currentPhase}</small>
                    </div>
                    <div className="activity-meter" aria-label={`${progressPercent}% of pipeline stages complete`}><span style={{ width: `${progressPercent}%` }} /></div>
                    <span className="activity-count">{derived.completedStageCount}/{derived.totalStages} stages</span>
                </div>

                <div className="run-layout">
                    <aside className="run-sidebar">
                        <PipelineGraph
                            selectedAnalysts={derived.selectedAnalysts}
                            finished={derived.finishedNodes}
                            current={derived.currentNode}
                            status={derived.status}
                            connected={connected}
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
                            stageProgress={{ completed: derived.completedStageCount, total: derived.totalStages }}
                            evidenceCount={evidenceCount}
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
            case "token": {
                const node = normalizePipelineNode(event.node);
                liveTextByNode[node] = (liveTextByNode[node] ?? "") + event.text;
                currentNode = node;
                break;
            }
            case "tool.started":
                currentNode = normalizePipelineNode(event.node);
                break;
            case "tool.finished":
                // Keep the analyst active: it may immediately make another
                // tool call or stream its final response after the tool returns.
                currentNode = normalizePipelineNode(event.node);
                break;
            case "node.finished": {
                const node = normalizePipelineNode(event.node);
                finishedNodes.add(node);
                if (currentNode === node) currentNode = null;
                break;
            }
            case "report":
                reports[event.key] = event.content;
                currentNode = REPORT_NODE_BY_KEY[event.key] ?? currentNode;
                break;
            case "debate.turn":
                debateTurns.push({ debate: event.debate, speaker: event.speaker, content: event.content });
                currentNode = SPEAKER_NODE_BY_KEY[event.speaker] ?? currentNode;
                break;
            case "decision":
                rating = event.rating;
                decisionText = event.text;
                currentNode = "Portfolio Manager";
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
                currentNode = null;
                break;
            case "run.failed":
                failure = event.error;
                status = "failed";
                currentNode = null;
                break;
            default:
                break;
        }
    }

    const selectedStageNames = selectedAnalysts.map((key) => ANALYST_NAMES[key] ?? key);
    const stageNames = new Set([...selectedStageNames, ...POST_STAGE_NAMES]);
    const completedStages = new Set([...finishedNodes].filter((node) => stageNames.has(node)));
    const completedStageCount = completedStages.size;
    const totalStages = stageNames.size;
    const currentLive = currentNode ? liveTextByNode[currentNode] ?? "" : "";

    return {
        selectedAnalysts,
        finishedNodes: completedStages,
        completedStageCount,
        totalStages,
        currentNode,
        currentPhase: phaseForNode(currentNode, status),
        reports,
        reportCount: Object.keys(reports).length,
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

function normalizePipelineNode(node: string) {
    return TOOL_NODE_TO_STAGE[node] ?? node;
}

function phaseForNode(node: string | null, status: RunStatus) {
    if (!node) {
        if (status === "done") return "decision complete";
        if (status === "failed") return "run stopped";
        return "initializing pipeline";
    }
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
                                    <MarkdownContent content={turn.content} compact />
                                </div>
                            ))}
                        </div>
                    </article>
                ))}
            </div>
        </section>
    );
}
