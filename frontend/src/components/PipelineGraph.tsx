import { useMemo } from "react";

/**
 * The pipeline as a vertical list of stages, with the current stage lit.
 *
 * The graph is defined as the analyst chain (dynamic, based on selection)
 * followed by the fixed post-analyst nodes. "Current" comes from the most
 * recent token event; "finished" from node.finished events.
 */
const POST_ANALYSTS = [
    "Upside Case",
    "Downside Case",
    "Investment Lead",
    "Trader",
    "Growth Advocate",
    "Capital Steward",
    "Balanced Reviewer",
    "Portfolio Manager",
];

const ANALYST_LABEL: Record<string, string> = {
    market: "Market Analyst",
    social: "Sentiment Analyst",
    news: "News Analyst",
    fundamentals: "Fundamentals Analyst",
};

interface Props {
    selectedAnalysts: string[];
    finished: Set<string>;
    current: string | null;
}

export default function PipelineGraph({ selectedAnalysts, finished, current }: Props) {
    const stages = useMemo(() => {
        const analysts = selectedAnalysts.map((a) => ANALYST_LABEL[a] ?? a);
        return [...analysts, ...POST_ANALYSTS];
    }, [selectedAnalysts]);

    return (
        <ol className="space-y-1">
            {stages.map((name, i) => {
                const isFinished = finished.has(name);
                const isCurrent = current === name && !isFinished;
                return (
                    <li
                        key={name}
                        className={[
                            "flex items-center gap-3 rounded px-3 py-2 text-sm transition-colors",
                            isCurrent ? "bg-panel border border-accent" : "border border-transparent",
                            isFinished ? "text-slate-500" : "text-slate-200",
                        ].join(" ")}
                    >
                        <span className="w-6 text-xs text-slate-500 text-right">{i + 1}</span>
                        <span
                            className={[
                                "h-2 w-2 rounded-full",
                                isFinished ? "bg-slate-600" : isCurrent ? "bg-accent animate-pulse" : "bg-line",
                            ].join(" ")}
                        />
                        <span>{name}</span>
                    </li>
                );
            })}
        </ol>
    );
}