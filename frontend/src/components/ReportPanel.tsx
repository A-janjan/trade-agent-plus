const TITLES: Record<string, string> = {
    market_report: "Market Analyst",
    sentiment_report: "Sentiment Analyst",
    news_report: "News Analyst",
    fundamentals_report: "Fundamentals Analyst",
    investment_plan: "Investment Lead",
    trader_investment_plan: "Trader",
    final_trade_decision: "Portfolio Manager",
};

export default function ReportPanel({ reports }: { reports: Record<string, string> }) {
    const keys = Object.keys(TITLES).filter((k) => reports[k]);
    if (keys.length === 0) {
        return <div className="text-sm text-slate-500">No reports yet.</div>;
    }
    return (
        <div className="space-y-4">
            {keys.map((k) => (
                <details key={k} open={k === "final_trade_decision"} className="rounded border border-line bg-panel">
                    <summary className="cursor-pointer px-4 py-3 font-semibold border-b border-line">
                        {TITLES[k]}
                    </summary>
                    <div className="px-4 py-3 prose prose-invert prose-sm max-w-none whitespace-pre-wrap">
                        {reports[k]}
                    </div>
                </details>
            ))}
        </div>
    );
}