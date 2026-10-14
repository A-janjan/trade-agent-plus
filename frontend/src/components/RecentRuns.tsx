import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRuns } from "../api";
import type { RunSummary } from "../types";
import Icon from "./Icon";

function formatDate(value: string) {
    const parsed = new Date(`${value}T12:00:00`);
    return Number.isNaN(parsed.getTime())
        ? value
        : parsed.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatElapsed(seconds: number | null) {
    if (seconds == null) return "In progress";
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

export default function RecentRuns() {
    const [runs, setRuns] = useState<RunSummary[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        listRuns()
            .then((items) => {
                if (active) setRuns(items.slice(0, 5));
            })
            .catch(() => {
                // The API is optional while the frontend is being explored.
                // Keep the empty state useful instead of surfacing a fetch error.
            })
            .finally(() => {
                if (active) setLoading(false);
            });
        return () => {
            active = false;
        };
    }, []);

    return (
        <section className="recent-section" aria-labelledby="recent-runs-title">
            <div className="section-heading">
                <div>
                    <div className="eyebrow"><Icon name="history" size={14} /> Workspace history</div>
                    <h2 id="recent-runs-title">Recent runs</h2>
                </div>
                {runs.length > 0 && <span className="muted-label">{runs.length} latest</span>}
            </div>

            <div className="recent-list panel">
                {loading ? (
                    <div className="recent-empty"><Icon name="loader" size={18} className="spin" /><span>Loading workspace history…</span></div>
                ) : runs.length === 0 ? (
                    <div className="recent-empty">
                        <span className="empty-orb"><Icon name="activity" size={18} /></span>
                        <div>
                            <strong>No runs yet</strong>
                            <p>Start a research run above and its decision trail will live here.</p>
                        </div>
                    </div>
                ) : (
                    runs.map((run) => (
                        <Link className="recent-row" to={`/runs/${run.run_id}`} key={run.run_id}>
                            <span className="recent-symbol">{run.ticker.slice(0, 1)}</span>
                            <span className="recent-main">
                                <strong>{run.ticker}</strong>
                                <small>{formatDate(run.trade_date)} · {run.event_count} events</small>
                            </span>
                            <span className={`status-dot status-dot-${run.status}`} />
                            <span className="recent-status">
                                <strong>{run.rating ?? (run.status === "failed" ? "Failed" : "Running")}</strong>
                                <small>{formatElapsed(run.elapsed_seconds)}</small>
                            </span>
                            <Icon name="chevronRight" size={16} className="recent-chevron" />
                        </Link>
                    ))
                )}
            </div>
        </section>
    );
}
