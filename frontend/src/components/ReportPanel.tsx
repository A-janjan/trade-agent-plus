import Icon, { type IconName } from "./Icon";

const REPORTS: { key: string; title: string; phase: string; icon: IconName }[] = [
    { key: "market_report", title: "Market Analyst", phase: "Analyst team", icon: "trend" },
    { key: "sentiment_report", title: "Sentiment Analyst", phase: "Analyst team", icon: "pulse" },
    { key: "news_report", title: "News Analyst", phase: "Analyst team", icon: "globe" },
    { key: "fundamentals_report", title: "Fundamentals Analyst", phase: "Analyst team", icon: "layers" },
    { key: "investment_plan", title: "Investment Lead", phase: "Research debate", icon: "spark" },
    { key: "trader_investment_plan", title: "Trader", phase: "Action plan", icon: "zap" },
    { key: "final_trade_decision", title: "Portfolio Manager", phase: "Final call", icon: "shield" },
];

export default function ReportPanel({ reports }: { reports: Record<string, string> }) {
    const available = REPORTS.filter(({ key }) => reports[key]);

    return (
        <section className="reports-section" aria-labelledby="reports-title">
            <div className="content-heading">
                <div>
                    <div className="eyebrow"><Icon name="fileText" size={14} /> Evidence archive</div>
                    <h2 id="reports-title">Research reports</h2>
                </div>
                <span className="report-count">{available.length} available</span>
            </div>
            {available.length === 0 ? (
                <div className="empty-panel panel"><Icon name="fileText" size={19} /><span>Reports will appear as each node completes.</span></div>
            ) : (
                <div className="report-list">
                    {available.map((report, index) => (
                        <details className={`report-item panel ${report.key === "final_trade_decision" ? "is-final" : ""}`} key={report.key} open={report.key === "final_trade_decision" || index === 0}>
                            <summary>
                                <span className="report-icon"><Icon name={report.icon} size={16} /></span>
                                <span className="report-heading">
                                    <strong>{report.title}</strong>
                                    <small>{report.phase}</small>
                                </span>
                                <span className="report-summary-meta">{reports[report.key].length.toLocaleString()} chars</span>
                                <Icon name="chevronDown" size={16} className="report-chevron" />
                            </summary>
                            <div className="report-content"><pre>{reports[report.key]}</pre></div>
                        </details>
                    ))}
                </div>
            )}
        </section>
    );
}
