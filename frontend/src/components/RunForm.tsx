import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { startRun } from "../api";

const ANALYSTS = ["market", "social", "news", "fundamentals"] as const;

export default function RunForm() {
    const navigate = useNavigate();
    const [ticker, setTicker] = useState("NVDA");
    const [tradeDate, setTradeDate] = useState(new Date().toISOString().slice(0, 10));
    const [analysts, setAnalysts] = useState<string[]>([...ANALYSTS]);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function submit(e: React.FormEvent) {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
            const run = await startRun({
                ticker: ticker.trim(),
                trade_date: tradeDate,
                selected_analysts: analysts,
            });
            navigate(`/runs/${run.run_id}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
            setBusy(false);
        }
    }

    return (
        <form onSubmit={submit} className="rounded-lg border border-line bg-panel p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <label className="space-y-1">
                    <span className="text-xs uppercase tracking-wide text-slate-400">Ticker</span>
                    <input
                        value={ticker}
                        onChange={(e) => setTicker(e.target.value.toUpperCase())}
                        className="w-full rounded bg-ink border border-line px-3 py-2 font-mono"
                        required
                    />
                </label>
                <label className="space-y-1">
                    <span className="text-xs uppercase tracking-wide text-slate-400">Trade date</span>
                    <input
                        type="date"
                        value={tradeDate}
                        onChange={(e) => setTradeDate(e.target.value)}
                        className="w-full rounded bg-ink border border-line px-3 py-2"
                        required
                    />
                </label>
            </div>

            <div className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-slate-400">Analysts</span>
                <div className="flex gap-3">
                    {ANALYSTS.map((a) => (
                        <label key={a} className="flex items-center gap-2 text-sm">
                            <input
                                type="checkbox"
                                checked={analysts.includes(a)}
                                onChange={(e) =>
                                    setAnalysts((prev) =>
                                        e.target.checked ? [...prev, a] : prev.filter((x) => x !== a)
                                    )
                                }
                            />
                            {a}
                        </label>
                    ))}
                </div>
            </div>

            {error && <div className="text-bear text-sm">{error}</div>}

            <button
                type="submit"
                disabled={busy || analysts.length === 0}
                className="rounded bg-accent text-ink font-semibold px-4 py-2 disabled:opacity-50"
            >
                {busy ? "Starting…" : "Run"}
            </button>
        </form>
    );
}