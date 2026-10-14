import { useMemo } from "react";
import Icon, { type IconName } from "./Icon";

const POST_ANALYSTS = [
    { name: "Upside Case", short: "Upside", group: "Research debate", icon: "arrowUpRight" as IconName },
    { name: "Downside Case", short: "Downside", group: "Research debate", icon: "arrowDown" as IconName },
    { name: "Investment Lead", short: "Investment lead", group: "Research debate", icon: "spark" as IconName },
    { name: "Trader", short: "Trader", group: "Action plan", icon: "zap" as IconName },
    { name: "Growth Advocate", short: "Growth", group: "Risk debate", icon: "trend" as IconName },
    { name: "Capital Steward", short: "Capital", group: "Risk debate", icon: "shield" as IconName },
    { name: "Balanced Reviewer", short: "Balanced", group: "Risk debate", icon: "eye" as IconName },
    { name: "Portfolio Manager", short: "Portfolio manager", group: "Risk debate", icon: "layers" as IconName },
];

const ANALYST_LABEL: Record<string, { name: string; short: string; icon: IconName }> = {
    market: { name: "Market Analyst", short: "Market", icon: "trend" },
    social: { name: "Sentiment Analyst", short: "Sentiment", icon: "pulse" },
    news: { name: "News Analyst", short: "News", icon: "globe" },
    fundamentals: { name: "Fundamentals Analyst", short: "Fundamentals", icon: "layers" },
};

interface Props {
    selectedAnalysts: string[];
    finished: Set<string>;
    current: string | null;
    status: "running" | "done" | "failed";
}

export default function PipelineGraph({ selectedAnalysts, finished, current, status }: Props) {
    const stages = useMemo(
        () => [
            ...selectedAnalysts.map((key) => {
                const analyst = ANALYST_LABEL[key] ?? { name: key, short: key, icon: "activity" as IconName };
                return { ...analyst, name: analyst.name, group: "Analyst team" };
            }),
            ...POST_ANALYSTS,
        ],
        [selectedAnalysts],
    );
    const complete = stages.filter((stage) => finished.has(stage.name)).length;

    return (
        <section className="pipeline-card panel" aria-label="Analysis pipeline">
            <div className="pipeline-heading">
                <div>
                    <div className="eyebrow"><Icon name="activity" size={14} /> Pipeline</div>
                    <h2>Decision path</h2>
                </div>
                <span className="pipeline-count">{complete}/{stages.length}</span>
            </div>
            <div className="pipeline-progress"><span style={{ width: `${stages.length ? (complete / stages.length) * 100 : 0}%` }} /></div>

            <ol className="pipeline-list">
                {stages.map((stage, index) => {
                    const isFinished = finished.has(stage.name);
                    const isCurrent = current === stage.name && !isFinished;
                    const previousGroup = stages[index - 1]?.group;
                    const showGroup = index === 0 || previousGroup !== stage.group;
                    return (
                        <li className="pipeline-item-wrap" key={stage.name}>
                            {showGroup && <div className="pipeline-group-label">{stage.group}</div>}
                            <div className={`pipeline-item ${isFinished ? "is-finished" : ""} ${isCurrent ? "is-current" : ""}`}>
                                <span className="pipeline-index">
                                    {isFinished ? <Icon name="check" size={13} /> : String(index + 1).padStart(2, "0")}
                                </span>
                                <span className="pipeline-stage-icon"><Icon name={stage.icon} size={15} /></span>
                                <span className="pipeline-stage-copy">
                                    <strong>{stage.short}</strong>
                                    {isCurrent && <small>Streaming now</small>}
                                </span>
                                {isCurrent && <span className="current-wave"><i /><i /><i /></span>}
                            </div>
                        </li>
                    );
                })}
            </ol>
            <div className="pipeline-footer">
                <span className={`pipeline-state pipeline-state-${status}`}><span />{status === "running" ? "Live analysis" : status === "done" ? "Run complete" : "Run failed"}</span>
                <span className="pipeline-live-label">SSE connected</span>
            </div>
        </section>
    );
}
