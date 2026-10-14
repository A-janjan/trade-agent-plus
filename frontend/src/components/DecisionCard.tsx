import Icon from "./Icon";
import type { RunStatus } from "../types";

function ratingTone(rating: string | null) {
    if (!rating) return "neutral";
    if (rating.toLowerCase().includes("buy")) return "bull";
    if (rating.toLowerCase().includes("sell")) return "bear";
    return "neutral";
}

function formatElapsed(seconds: number | null) {
    if (seconds == null) return "measuring…";
    if (seconds < 60) return `${seconds.toFixed(1)}s elapsed`;
    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s elapsed`;
}

interface Props {
    rating: string | null;
    text: string;
    elapsed: number | null;
    status: RunStatus;
    eventCount: number;
    error?: string | null;
}

export default function DecisionCard({ rating, text, elapsed, status, eventCount, error }: Props) {
    const tone = ratingTone(rating);
    const isPending = status === "running" && !rating && !text;
    const title = status === "failed" ? "Run stopped" : rating ?? (isPending ? "Decision in progress" : "No rating returned");

    return (
        <section className={`decision-card decision-card-${tone} ${status === "failed" ? "decision-card-failed" : ""}`}>
            <div className="decision-topline">
                <div className="eyebrow"><Icon name="sparkles" size={14} /> Portfolio manager</div>
                <div className={`decision-status decision-status-${status}`}>
                    <span className="status-pip" />
                    {status === "running" ? "Working" : status === "done" ? "Complete" : "Needs attention"}
                </div>
            </div>

            <div className="decision-body">
                <div className="decision-rating-wrap">
                    <span className="decision-caption">Current stance</span>
                    <h2 className="decision-rating">{title}</h2>
                    {isPending && (
                        <div className="decision-waiting"><span className="waiting-bar" /><span>Waiting for the final risk review</span></div>
                    )}
                    {status === "failed" && error && <p className="decision-error">{error}</p>}
                </div>
                <div className="decision-mark" aria-hidden="true">
                    {status === "failed" ? <Icon name="alert" size={25} /> : rating ? <Icon name="check" size={28} /> : <Icon name="pulse" size={26} />}
                </div>
            </div>

            {text && <pre className="decision-text">{text}</pre>}

            <div className="decision-footer">
                <span><Icon name="clock" size={14} /> {formatElapsed(elapsed)}</span>
                <span><Icon name="activity" size={14} /> {eventCount} stream events</span>
                <span className="decision-footer-note">Evidence before conviction</span>
            </div>
        </section>
    );
}
