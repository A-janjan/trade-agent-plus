import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { startRun } from "../api";
import Icon, { type IconName } from "./Icon";

const ANALYSTS = [
    {
        id: "market",
        label: "Market",
        description: "Price action & momentum",
        icon: "trend" as IconName,
    },
    {
        id: "social",
        label: "Sentiment",
        description: "Crowd & social signals",
        icon: "pulse" as IconName,
    },
    {
        id: "news",
        label: "News",
        description: "Events & macro context",
        icon: "globe" as IconName,
    },
    {
        id: "fundamentals",
        label: "Fundamentals",
        description: "Statements & quality",
        icon: "layers" as IconName,
    },
] as const;

const TICKER_SUGGESTIONS = ["NVDA", "AAPL", "SPY", "BTC-USD"];

function localDateString() {
    const now = new Date();
    const month = `${now.getMonth() + 1}`.padStart(2, "0");
    const day = `${now.getDate()}`.padStart(2, "0");
    return `${now.getFullYear()}-${month}-${day}`;
}

export default function RunForm() {
    const navigate = useNavigate();
    const today = localDateString();
    const [ticker, setTicker] = useState("NVDA");
    const [tradeDate, setTradeDate] = useState(today);
    const [analysts, setAnalysts] = useState<string[]>(ANALYSTS.map(({ id }) => id));
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    function toggleAnalyst(id: string) {
        setAnalysts((current) =>
            current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
        );
    }

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const normalizedTicker = ticker.trim().toUpperCase();
        if (!normalizedTicker) {
            setError("Add a ticker symbol to start the run.");
            return;
        }
        if (analysts.length === 0) {
            setError("Choose at least one research lens.");
            return;
        }

        setBusy(true);
        setError(null);
        try {
            const run = await startRun({
                ticker: normalizedTicker,
                trade_date: tradeDate,
                selected_analysts: analysts,
            });
            navigate(`/runs/${run.run_id}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : "The run could not be started.");
            setBusy(false);
        }
    }

    return (
        <form className="run-form panel panel-glow" onSubmit={submit}>
            <div className="form-heading">
                <div>
                    <div className="eyebrow"><span className="eyebrow-dot" /> New research run</div>
                    <h2>Set your point of view</h2>
                </div>
                <span className="live-chip"><span /> live stream</span>
            </div>

            <div className="form-fields">
                <label className="field-group">
                    <span className="field-label">Instrument</span>
                    <span className="input-wrap input-wrap-symbol">
                        <span className="input-prefix">$</span>
                        <input
                            value={ticker}
                            onChange={(event) => setTicker(event.target.value.toUpperCase())}
                            className="text-input symbol-input"
                            placeholder="NVDA"
                            autoComplete="off"
                            spellCheck={false}
                            pattern="[A-Za-z0-9.^=\\-]{1,32}"
                            aria-label="Ticker symbol"
                            required
                        />
                    </span>
                </label>
                <label className="field-group">
                    <span className="field-label">Analysis date</span>
                    <span className="input-wrap">
                        <Icon name="calendar" size={16} />
                        <input
                            type="date"
                            value={tradeDate}
                            max={today}
                            onChange={(event) => setTradeDate(event.target.value)}
                            className="text-input"
                            aria-label="Analysis date"
                            required
                        />
                    </span>
                </label>
            </div>

            <div className="suggestions" aria-label="Suggested tickers">
                <span className="suggestions-label">Try</span>
                {TICKER_SUGGESTIONS.map((suggestion) => (
                    <button
                        className={`suggestion ${ticker === suggestion ? "is-selected" : ""}`}
                        key={suggestion}
                        type="button"
                        onClick={() => setTicker(suggestion)}
                    >
                        {suggestion}
                    </button>
                ))}
            </div>

            <div className="analyst-heading">
                <div>
                    <span className="field-label">Research lenses</span>
                    <span className="field-help">Select the evidence your team should weigh.</span>
                </div>
                <button
                    type="button"
                    className="text-button"
                    onClick={() =>
                        setAnalysts(analysts.length === ANALYSTS.length ? [] : ANALYSTS.map(({ id }) => id))
                    }
                >
                    {analysts.length === ANALYSTS.length ? "Clear all" : "Select all"}
                </button>
            </div>

            <div className="analyst-grid">
                {ANALYSTS.map((analyst) => {
                    const selected = analysts.includes(analyst.id);
                    return (
                        <button
                            className={`analyst-option ${selected ? "is-selected" : ""}`}
                            key={analyst.id}
                            type="button"
                            aria-pressed={selected}
                            onClick={() => toggleAnalyst(analyst.id)}
                        >
                            <span className="analyst-icon"><Icon name={analyst.icon} size={17} /></span>
                            <span className="analyst-copy">
                                <strong>{analyst.label}</strong>
                                <small>{analyst.description}</small>
                            </span>
                            <span className="analyst-check"><Icon name="check" size={13} /></span>
                        </button>
                    );
                })}
            </div>

            {error && (
                <div className="form-error" role="alert">
                    <Icon name="alert" size={16} />
                    <span>{error}</span>
                </div>
            )}

            <div className="form-footer">
                <div className="form-note">
                    <Icon name="clock" size={15} />
                    <span>Typical run: a few minutes</span>
                </div>
                <button className="primary-button" type="submit" disabled={busy || analysts.length === 0}>
                    {busy ? <Icon name="loader" size={17} className="spin" /> : <Icon name="play" size={15} />}
                    <span>{busy ? "Preparing run…" : "Start analysis"}</span>
                    {!busy && <Icon name="arrowUpRight" size={15} />}
                </button>
            </div>
            <p className="form-disclaimer">Research output only · no orders are placed</p>
        </form>
    );
}
