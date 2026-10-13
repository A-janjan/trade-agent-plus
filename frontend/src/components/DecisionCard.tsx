const RATING_COLOR: Record<string, string> = {
    "Strong Buy": "text-bull",
    "Buy": "text-bull",
    "Hold": "text-neut",
    "Sell": "text-bear",
    "Strong Sell": "text-bear",
};

export default function DecisionCard({
    rating, text, elapsed,
}: { rating: string | null; text: string; elapsed: number | null }) {
    if (!rating && !text) return null;
    const color = rating ? RATING_COLOR[rating] ?? "text-slate-300" : "text-slate-300";
    return (
        <div className="rounded-lg border-2 border-accent bg-panel p-6 space-y-3">
            <div className="flex items-baseline justify-between">
                <div className={`text-3xl font-bold ${color}`}>{rating ?? "—"}</div>
                {elapsed != null && (
                    <div className="text-xs text-slate-500">{elapsed.toFixed(1)}s</div>
                )}
            </div>
            {text && (
                <pre className="whitespace-pre-wrap text-sm text-slate-300">{text}</pre>
            )}
        </div>
    );
}