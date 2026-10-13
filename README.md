<div align="center">

# tradeagents

**A multi-agent LLM research framework for equity and crypto markets.**

Four analysts investigate. Two researchers challenge the evidence. A trader proposes an action, three risk reviewers stress-test it, and a portfolio manager makes the final call.

Every decision is recorded, evaluated once its holding window has elapsed, and used as context for later runs on the same ticker.

[Quick start](#quick-start) · [Architecture](#how-it-works) · [Providers](#supported-llm-providers) · [CLI](#cli-usage) · [Python API](#python-api) · [Web UI](#web-ui) · [Data & memory](#data-vendors) · [Backtesting](#backtesting) · [Configuration](#configuration) · [Development](#development)

</div>

---

## What this is

`tradeagents` is a research framework for examining how large language models reason about markets when independent analysts and adversarial debates challenge one another's conclusions.

Each run takes a ticker and an analysis date, produces four independent

analyst reports, runs an adversarial debate over them, converts the verdict

into a transaction proposal, then holds a second debate about the proposal's

risk. The final rating is logged. Once the holding window has traded, the

outcome is measured against a regional benchmark and reflected on — and the

reflection is injected into the next run for the same ticker.

**This is a research and decision-evaluation tool, not an execution system.** It does not route orders, simulate fills, or maintain a live position ledger. It produces a rating, thesis, supporting evidence, and an auditable report trail.

### What's inside

| Layer | What it does |
|---|---|
| **Analysts** | Market (technical), Sentiment (social + news), News (events + macro), Fundamentals (statements) |
| **Research debate** | Upside case vs. downside case, both grounded in the analyst reports |
| **Investment Lead** | Synthesizes the debate into a 5-tier stance with risks and catalysts |
| **Trader** | Converts the stance into a concrete action with entry, stop, sizing |
| **Risk debate** | Growth Advocate vs. Capital Steward vs. Balanced Reviewer |
| **Portfolio Manager** | Issues the final rating, executive summary, and thesis |
| **Memory** | Every decision logged, settled, reflected on, and re-injected |
| **Backtest** | Grid runner and scoring by rating |
| **API + Web UI** | Live streaming view over SSE, decision history, backtest dashboard |
| **Observability** | Optional Langfuse tracing of every node, LLM call, and tool call |
---

## How it works

```
                     ┌──────────────────────────────────────────────┐
                     │               Analyst Team                   │
                     │                                              │
  ┌──────────┐       │   ┌─────────┐  ┌──────────┐  ┌──────────┐   │
  │  ticker  │──────▶│   │ Market  │  │Sentiment │  │   News   │   │
  │   date   │       │   └────┬────┘  └────┬─────┘  └────┬─────┘   │
  └──────────┘       │        │            │             │         │
                     │        ▼            ▼             ▼         │
                     │   ┌───────────────────────────────────┐    │
                     │   │        Fundamentals               │    │
                     │   └───────────────┬───────────────────┘    │
                     └───────────────────┼────────────────────────┘
                                         │
                     ┌───────────────────▼────────────────────────┐
                     │            Research Debate                 │
                     │    ┌────────────┐      ┌────────────┐      │
                     │    │Upside Case │◀────▶│Downside C. │      │
                     │    └─────┬──────┘      └──────┬─────┘      │
                     │          └────────┬───────────┘            │
                     │                   ▼                        │
                     │          ┌─────────────────┐               │
                     │          │ Investment Lead │               │
                     │          └────────┬────────┘               │
                     └───────────────────┼────────────────────────┘
                                         │
                     ┌───────────────────▼────────────────────────┐
                     │              Trader                        │
                     │  Action · Entry · Stop · Sizing            │
                     └───────────────────┬────────────────────────┘
                                         │
                     ┌───────────────────▼────────────────────────┐
                     │             Risk Debate                    │
                     │  Growth ◀──▶ Capital ◀──▶ Balanced         │
                     │                   │                        │
                     │          ┌────────▼────────┐               │
                     │          │Portfolio Manager│               │
                     │          └────────┬────────┘               │
                     └───────────────────┼────────────────────────┘
                                         │
                                         ▼
                            ╔════════════════════════╗
                            ║   Final Decision       ║
                            ║   Strong Buy … Sell    ║
                            ╚════════════┬═══════════╝
                                         │
                                         ▼
                     ┌───────────────────────────────────────────┐
                     │  Memory: log · settle · reflect · inject  │
                     └───────────────────────────────────────────┘
```

Two design choices drive most of the rest:

**The debate machinery is generic.** A debate is an ordered list of

participants and a transcript. Round numbers are derived from position; the

next speaker is derived from the last entry. The same module runs the

two-sided research debate and the three-sided risk debate; a third debate

would be a new participant list, not new code.

**The decision log is the results table.** A run records its decision.

A later run settles it with realized return and alpha. Scoring reads what

the log already contains. Nothing is duplicated.

---

## Quick start

### Prerequisites

- Python 3.11 or newer

- An API key for one supported LLM provider (OpenAI is the default)

- Optional: `FRED_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `TYPESAFE_API_KEY`

### Install

```bash
git clone https\://github.com/a-janjan/tradeagents.git
cd tradeagents
\# with uv (recommended)
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
\# or with plain pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Configure

```bash
cp .env.example .env
```

Then edit `.env` and set at least:

```bash
OPENAI_API_KEY=sk-...
```

### Run

```bash
\# one analysis, live progress in the terminal
python -m tradeagents NVDA 2026-09-01
\# save the report tree to disk
python -m tradeagents NVDA 2026-09-01 --save
\# with only the market and news analysts
python -m tradeagents NVDA 2026-09-01 --analysts=market,news
```

### See the web UI

```bash
\# terminal 1: the API
uvicorn tradeagents.api.main:app --reload --port 8000
\# terminal 2: the frontend
cd frontend
npm install
npm run dev
```

Open [http\://localhost:5173](http\://localhost:5173). Submitting the form

navigates to a live page where each pipeline stage lights up as it runs, the

active node's text streams into a preview panel, debate turns appear as

labelled blocks, and the decision card fills in when the Portfolio Manager

finishes.

---

## Supported LLM providers

| Provider | Key | Notes |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | Default. Uses the Responses API for native models. |
| Anthropic | `ANTHROPIC_API_KEY` | Claude 4.6+ and Claude 5 support the `effort` parameter. |
| Google | `GOOGLE_API_KEY` | Gemini 3.x. `thinking_level` on Flash models. |
| xAI | `XAI_API_KEY` | Grok. |
| DeepSeek | `DEEPSEEK_API_KEY` | Thinking models carry reasoning state across turns. |
| Qwen | `DASHSCOPE_API_KEY` | International endpoint. |
| Qwen (China) | `DASHSCOPE_CN_API_KEY` | Mainland endpoint. |
| GLM | `ZHIPU_API_KEY` | Z.AI, international. |
| GLM (China) | `ZHIPU_CN_API_KEY` | BigModel. |
| MiniMax | `MINIMAX_API_KEY` | M2.x reasoning models. |
| Kimi | `MOONSHOT_API_KEY` | Moonshot. |
| Mistral | `MISTRAL_API_KEY` | |
| Groq | `GROQ_API_KEY` | |
| NVIDIA | `NVIDIA_API_KEY` | NIM. |
| OpenRouter | `OPENROUTER_API_KEY` | |
| Azure OpenAI | see below | |
| AWS Bedrock | see below | |
| Ollama | — | Local. `OLLAMA_BASE_URL` for a remote host. |
| OpenAI-compatible | — | Any vLLM / LM Studio / llama.cpp / relay. |
<details>

<summary><b>Azure OpenAI</b></summary>

Copy `.env.enterprise.example` to `.env.enterprise` and fill in:

```bash
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https\://<resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=...
OPENAI_API_VERSION=2025-03-01-preview
```

Then set `llm_provider: "azure"`.

</details>

<details>

<summary><b>AWS Bedrock</b></summary>

```bash
pip install -e ".[bedrock]"
```

Set `llm_provider: "bedrock"`. Authentication is either

`AWS_BEARER_TOKEN_BEDROCK` (no access keys needed) or the standard AWS

credential chain. Set `AWS_DEFAULT_REGION`. Use a Bedrock model ID such as

`us.anthropic.claude-opus-4-8-v1:0`.

</details>

<details>

<summary><b>Ollama and OpenAI-compatible servers</b></summary>

```bash
\# Ollama
llm_provider: "ollama"
OLLAMA_BASE_URL=http\://localhost:11434/v1   # optional; localhost by default
\# vLLM, LM Studio, llama.cpp, or any compatible relay
llm_provider: "openai_compatible"
backend_url: "http\://localhost:8000/v1"     # vLLM
backend_url: "http\://localhost:1234/v1"     # LM Studio
```

No key is required for local servers. Set `OPENAI_COMPATIBLE_API_KEY` if

your relay needs one.

</details>

---

## CLI usage

```
python -m tradeagents TICKER YYYY-MM-DD [options]
Options:
  --analysts=a,b,c    Select analysts (default: market,social,news,fundamentals)
  --no-display        Suppress the live progress display
  --save[=PATH]       Write the report tree; default is a timestamped directory
                      under results_dir
  --debug             Verbose per-node printing
```

### Backtest

```bash
python -m tradeagents.backtest NVDA,AAPL \\
    --start 2026-06-01 \\
    --end   2026-08-01 \\
    --every 7
```

`--run-id=ID` resumes an interrupted sweep. Cells already written to that

run's log are skipped, so re-launching continues from where it left off.

### What a run produces

```
\~/.tradeagents/logs/reports/NVDA_20261013_143055/
├── complete_report.md          ← the whole run, readable top to bottom
├── run.json                    ← ticker, date, rating, models, config snapshot
├── 01_analysts/
│   ├── market.md
│   ├── sentiment.md
│   ├── news.md
│   └── fundamentals.md
├── 06_research/
│   ├── upside.md
│   ├── downside.md
│   └── lead.md
├── 08_trading/
│   └── trader.md
├── 09_risk/
│   ├── growth.md
│   ├── capital.md
│   └── balanced.md
└── 12_portfolio/
    └── decision.md
```

---

## Python API

```python
from tradeagents.graph.trading_graph import TradingGraph
from tradeagents.default_config import DEFAULT_CONFIG
from tradeagents.portfolio import PortfolioContext
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["deep_think_llm"] = "gpt-4o"
config["quick_think_llm"] = "gpt-4o-mini"
config["max_debate_rounds"] = 2
graph = TradingGraph(
    selected_analysts=("market", "news"),
    config=config,
    debug=False,
)
\# Optional: give the trader and PM a book to size against
book = PortfolioContext.model_validate({
    "cash": 25_000.0,
    "currency": "USD",
    "positions": [{"ticker": "NVDA", "quantity": 120, "average_price": 150.0}],
})
final_state, decision = graph.propagate(
    "NVDA", "2026-09-01", portfolio=book,
)
print(decision)
graph.save_reports(final_state, "NVDA")
```

### Backtest programmatically

```python
from tradeagents.backtest import iter_grid, run_backtest, summarize
dates = iter_grid("2026-06-01", "2026-08-01", every_n_days=7)
result = run_backtest(
    ["NVDA", "AAPL"], dates, config,
    selected_analysts=["market", "news"],
)
print(summarize(result).render())
```

### Portfolio context

A portfolio is optional. When you pass one, the trader sizes against it; when

you don't, the prompts say so explicitly and the trader falls back to a

standard allocation. Three states are distinguished:

- a **position** — sized against directly

- a **flat book** — `positions: []`, meaning "no holdings, told you so"

- **no context** — nothing passed, meaning "you don't know"

Absence and flatness are not the same fact, so the pipeline never conflates

them.

---

## Web UI

Two services:

```bash
\# Backend
uvicorn tradeagents.api.main:app --port 8000
\# Frontend
cd frontend && npm run dev
```

The frontend runs on `:5173` and proxies `/api` to `:8000`, so SSE streams

work without CORS in development.

### Pages

**Run view** (`/runs/:id`)

- **Pipeline graph** — a vertical list of stages, lit as each runs, greyed

  as each finishes.

- **Live preview** — the active node's streamed text, scrolling.

- **Debate panels** — turns appear as labelled blocks as they are spoken.

- **Report panel** — collapsible sections, filled as each analyst completes.

- **Decision card** — the final rating, styled by direction, at the top.

**API endpoints**

| Endpoint | What |
|---|---|
| `POST /api/runs` | Start a run |
| `GET /api/runs` | List runs |
| `GET /api/runs/{id}` | Run summary + full state |
| `GET /api/runs/{id}/stream` | SSE event stream (replays history on connect) |
| `GET /api/runs/{id}/events` | Full event log as JSON |
| `DELETE /api/runs/{id}` | Cancel a run |
| `GET /api/decisions` | Decision log entries, filterable by ticker |
| `GET /api/decisions/markdown` | Human-readable log |
| `POST /api/decisions/settle` | Force a settlement pass |
| `POST /api/backtests` | Start a sweep |
| `GET /api/backtests/{id}` | Backtest status + summary |
Streaming is Server-Sent Events. A client that connects mid-run gets the

history first, then live events; a client that connects after the run

finishes gets the history and an immediate clean close.

---

## Data vendors

| Category | Vendors | Purpose |
|---|---|---|
| `core_stock_apis` | yfinance, alpha_vantage | OHLCV prices |
| `technical_indicators` | yfinance, alpha_vantage | RSI, MACD, Bollinger, etc. |
| `fundamental_data` | yfinance, alpha_vantage, sec_edgar | Statements and overviews |
| `news_data` | yfinance, alpha_vantage | Ticker news and global macro |
| `macro_data` | fred | Policy rates, CPI, unemployment, yields |
| `prediction_markets` | polymarket | Market-implied event probabilities |
**The vendor chain is explicit.** A call is served by the first configured

vendor that succeeds; the router never silently falls back to a vendor you

did not choose. To enable fallback, list vendors in order:

```python
config["data_vendors"]["core_stock_apis"] = "yfinance,alpha_vantage"
```

### SEC EDGAR

US fundamentals can come from SEC EDGAR, which reports each fact with its

**filing date**. A run dated in the past reads statements as they were on

file by then — including restatements at the vintage that was current.

Yahoo and Alpha Vantage do not carry filing dates, so the newest period may

postdate the analysis date; the vendor's header says so.

```python
config["data_vendors"]["fundamental_data"] = "sec_edgar,yfinance"
```

```bash
SEC_EDGAR_USER_AGENT="Your Name your@email.com"
```

### FRED point-in-time

Macroeconomic series are revised. FRED reports every observation with its

publication date, so a historical run can ask for the vintage that was

current then. Without this, a backtest would read today's revised GDP as if

it had been known at the time.

```bash
FRED_API_KEY=...
```

---

## Memory and learning

Every completed run is appended to a JSONL decision log at

`\~/.tradeagents/memory/decisions.jsonl` (override with

`TRADEAGENTS_MEMORY_LOG`).

The next run for the same ticker:

1. **Settles** any pending decisions whose holding window has now traded —

   fetches the realized return and alpha against the regional benchmark,

   generates a short reflection, and marks the entry settled.

2. **Injects** recent same-ticker decisions and cross-ticker lessons into

   the Portfolio Manager's prompt.

3. **Records** its own decision for a future run to settle.

Historical runs filter the injected lessons to those whose outcome was

already known by the trade date, so a backtest does not learn from outcomes

that had not happened yet.

### Regional benchmarks

Alpha is measured against a benchmark chosen from the ticker's exchange

suffix:

| Suffix | Benchmark | Market |
|---|---|---|
| *\*(none)\** | SPY | US |
| `.T` | ^N225 | Tokyo |
| `.HK` | ^HSI | Hong Kong |
| `.L` | ^FTSE | London |
| `.TO` | ^GSPTSE | Toronto |
| `.AX` | ^AXJO | Australia |
| `.NS` | ^NSEI | India NSE |
| `.SS` / `.SZ` | Composite | China A-shares |
Override with `benchmark_ticker`, or change the map entirely via

`benchmark_map`.

---

## Backtesting

```bash
python -m tradeagents.backtest NVDA,AAPL \\
    --start 2026-06-01 --end 2026-08-01 --every 7
```

Output:

```
Sweeping 2 ticker(s) × 5 date(s) = 10 cells
run_id: 20261013_143055
run_dir: \~/.tradeagents/logs/backtest/20261013_143055
cells run: 10, skipped: 0, failed: 0
Resolved cells: 8 · pending: 2 · unscored: 0
  Buy: n=5, called direction 60%, mean alpha +1.24%
  Sell: n=2, called direction 50%, mean alpha -0.85%
  Hold: n=1, no direction claimed, mean alpha +0.02%
Pending cells are not scored above; re-run to settle them.
Alpha is realized over 5 trading days after each analysis date.
```

**What backtest measures, and what it doesn't.** It measures \*decision

quality\*: given a rating at a point in time, did the direction prove right

and did the instrument outperform its benchmark? It is not a portfolio

simulator. Turning a rating into a filled order needs a quantity, a fill

price, and a cash ledger — none of which the system has. Inventing them here

would put an execution model behind an evaluation tool.

---

## Observability

### Langfuse

Optional, and disabled by default. Install and configure:

```bash
pip install -e ".[observability]"
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=https\://cloud.langfuse.com     # EU
\# export LANGFUSE_HOST=https\://us.cloud.langfuse.com  # US
```

Runs appear in Langfuse as nested traces: every node, every LLM call, every

tool call. Runs are grouped by ticker via `langfuse_session_id`, so you can

see a ticker's history in one view.

Three-state control:

```bash
TRADEAGENTS_LANGFUSE=auto    # default: trace when both keys are set
TRADEAGENTS_LANGFUSE=on      # require credentials; raise if absent
TRADEAGENTS_LANGFUSE=off     # never trace
```

### Live progress display

The terminal shows a Rich live region during every run: one row per node,

elapsed time, tool-call count, and a rolling preview of the active node's

output. Suppress it with `--no-display`, or force streaming headless with

`TRADEAGENTS_STREAMING=true`.

---

## Configuration

Every key is settable from `DEFAULT_CONFIG`, from `config` in Python, or

from an environment variable.

### Environment overrides

| Variable | Config key | Notes |
|---|---|---|
| `TRADEAGENTS_LLM_PROVIDER` | `llm_provider` | `openai`, `anthropic`, `google`, … |
| `TRADEAGENTS_DEEP_THINK_LLM` | `deep_think_llm` | Used by the Investment Lead and PM |
| `TRADEAGENTS_QUICK_THINK_LLM` | `quick_think_llm` | Used by analysts, debaters, trader |
| `TRADEAGENTS_BACKEND_URL` | `backend_url` | Custom endpoint |
| `TRADEAGENTS_OUTPUT_LANGUAGE` | `output_language` | Report language; internal debate stays English |
| `TRADEAGENTS_MAX_DEBATE_ROUNDS` | `max_debate_rounds` | Research debate rounds |
| `TRADEAGENTS_MAX_RISK_ROUNDS` | `max_risk_discuss_rounds` | Risk debate rounds |
| `TRADEAGENTS_TEMPERATURE` | `temperature` | Forwarded to the provider |
| `TRADEAGENTS_STREAMING` | `streaming` | Token streaming |
| `TRADEAGENTS_LANGFUSE_ENABLED` | `langfuse_enabled` | `auto` / `on` / `off` |
| `TRADEAGENTS_MEMORY_LOG` | `memory_log_path` | Decision log location |
| `TRADEAGENTS_HOLDING_DAYS` | `holding_period_days` | Settlement window |
| `TRADEAGENTS_RESULTS_DIR` | `results_dir` | Base directory for outputs |
| `TRADEAGENTS_CACHE_DIR` | `data_cache_dir` | Vendor cache |
### Config keys worth knowing

```python
"max_debate_rounds": 1            # more rounds = longer runs, denser debates
"max_risk_discuss_rounds": 1
"output_language": "English"      # "Deutsch", "日本語", etc.
"holding_period_days": 5          # settlement window in trading days
"benchmark_ticker": None          # override the regional default
"data_vendors": { ... }           # per-category vendor chain
"tool_vendors": { ... }           # per-tool override of the category
```

---

## Extending

### Add an analyst

Two files and one registry entry:

```
agents/analysts/my_analyst.py
agents/analysts/prompts/my_analyst.txt
```

Then in `graph/setup.py`:

```python
ANALYST_REGISTRY["my"] = {
    "node": "My Analyst",
    "tools_node": "tools_my",       # or None for a tool-less analyst
    "clear_node": "Clear My",
    "factory": create_my_analyst,
    "tools": MY_TOOLS,
}
```

The graph builder walks the registry; it does not change.

### Add a data vendor

One module in `dataflows/vendors/`, one import and one row in the router:

```python
VENDOR_METHODS["get_stock_data"]["myvendor"] = my_get_stock_data
```

Vendors raise from the shared taxonomy (`NoMarketDataError`,

`VendorRateLimitError`, `VendorNotConfiguredError`) and the router reacts by

behavior, not by vendor name — no new `except` clause is needed.

### Add an LLM provider

OpenAI-compatible providers are a registry row:

```python
OPENAI_COMPATIBLE_PROVIDERS["myprovider"] = ProviderSpec(
    base_url="https\://api.myprovider.com/v1",
)
```

For a genuinely different API, subclass `BaseLLMClient` and add a branch to

`create_llm_client`.

---

## Reproducibility

Two runs of the same ticker and date will not produce identical text.

**Sources of variation:**

- Model sampling is non-deterministic. Even at fixed temperature, providers

  do not guarantee byte-identical output across calls.

- Live feeds move. News, StockTwits, and Reddit return different content

  over time; pinning the analysis date holds prices fixed but social and

  news feeds still reflect the present.

**Deterministic mechanisms:**

- Instrument identity (company name, sector, industry) is resolved

  deterministically from the ticker before any agent runs.

- Price and indicator windows are clamped to the analysis date; a model

  cannot walk past it, however it phrases a tool call.

- FRED macro data is pinned to the vintage known by the analysis date, not

  today's revision.

- SEC EDGAR fundamentals are served as filed, not as amended.

- The decision log reads a structured rating from the PM's typed output

  rather than parsing prose back into a label.

To reduce variation, lower `temperature`. Reasoning models largely ignore

it; for tighter reproducibility, name a non-reasoning model.

---

## Project layout

```
tradeagents/
├── agents/
│   ├── analysts/               ← market, sentiment, news, fundamentals
│   ├── researchers/            ← upside case, downside case, investment lead
│   ├── risk/                   ← growth, capital, balanced, portfolio manager
│   ├── trader/                 ← trader
│   ├── debate.py               ← shared debate machinery
│   ├── schemas.py              ← structured output types
│   ├── structured.py           ← structured-output helpers with fallback
│   ├── state.py                ← the graph state
│   ├── tools.py                ← LLM tool wrappers around the router
│   └── context.py              ← prompt context helpers
├── api/                        ← FastAPI + SSE
├── backtest/                   ← grid runner and scoring
├── dataflows/
│   ├── vendors/
│   │   ├── yahoo/              ← prices, indicators, fundamentals, news
│   │   ├── alpha_vantage/      ← same, as an alternative
│   │   ├── sec_edgar.py        ← statements as filed
│   │   ├── fred.py             ← macro series at vintage
│   │   ├── polymarket.py       ← event probabilities
│   │   ├── reddit.py           ← social posts
│   │   └── stocktwits.py       ← cashtag stream
│   ├── router.py               ← explicit vendor chain dispatch
│   ├── symbols.py              ← ticker normalization
│   ├── errors.py               ← vendor error taxonomy
│   ├── date_window.py          ← look-ahead-safe bounds
│   └── config.py               ← process-wide config
├── graph/
│   ├── setup.py                ← registries and graph construction
│   ├── trading_graph.py        ← top-level orchestration
│   └── progress.py             ← terminal display + event adapters
├── llm_clients/                ← provider factory
├── memory/
│   ├── log.py                  ← JSONL decision log
│   ├── settlement.py           ← outcome resolution
│   ├── reflection.py           ← lesson generation
│   └── context.py              ← past-context formatting
├── observability.py            ← optional Langfuse wiring
├── portfolio.py                ← the caller's book
├── reporting.py                ← report tree writer
├── default_config.py           ← defaults and env overrides
└── __main__.py                 ← CLI entry point
frontend/                       ← Vite + React + Tailwind
├── src/
│   ├── components/             ← RunForm, PipelineGraph, DecisionCard, …
│   ├── hooks/useRunStream.ts   ← SSE subscription
│   ├── pages/RunPage.tsx       ← the live run view
│   ├── api.ts
│   └── types.ts
└── …
```

---

## Design principles

A few decisions that shaped the codebase, worth knowing before you change

something.

**Absence is not emptiness.** A missing report is not a report that found

nothing. A missing portfolio is not a flat book. Every place a value can be

absent, the code says so explicitly rather than passing an empty string

through, because a model reads an empty section as a finding.

**The transcript is the only state.** A debate stores a list of turns.

Round number is derived from position; the next speaker is derived from the

last entry. There is no counter to fall out of sync with the transcript,

because a counter and a list can only disagree.

**Behavior, not names.** The router catches error *\*types\**, not vendor

names. Adding a vendor never requires touching the router. Adding a debate

never requires touching the graph builder. Adding an analyst is a registry

row.

**Point-in-time means point-in-time.** Prices are cut at the analysis date.

Fundamentals are cut at their filing date where the vendor supports it.

Macro series are pinned to the vintage that was current. The pipeline

refuses to serve a number the run could not have known.

**Structured where it helps, prose where it doesn't.** The five decision

agents (Investment Lead, Trader, Portfolio Manager) emit typed output so

downstream consumers read fields rather than regex. The four analysts emit

prose, because the reader is a human and the content is the analysis.

**The log is the source of truth.** Everything downstream of a decision —

settlement, reflection, backtest scoring, the PM's past context — reads from

the same JSONL the pipeline writes. There is no parallel record that can

drift from what actually happened.

---

## Development

```bash
\# install dev extras
uv pip install -e ".[dev]"
\# run the fast test suite
pytest -m unit
\# lint
ruff check .
ruff format .
\# API tests need the extra dependency
uv pip install -e ".[dev,api]"
pytest tests/test_api.py
```

### Running the frontend in development

```bash
cd frontend
npm install
npm run dev     # http\://localhost:5173, proxies /api to :8000
```

### Docker

```bash
docker compose run --rm tradingagents
```

For a local model served by Ollama in the same compose project:

```bash
docker compose --profile ollama run --rm tradingagents-ollama
```

---

## Markets and tickers

Any instrument Yahoo Finance covers, using the exchange-suffixed ticker:

| Market | Example |
|---|---|
| US | `AAPL`, `NVDA`, `SPY` |
| Hong Kong | `0700.HK` |
| Tokyo | `7203.T` |
| London | `AZN.L` |
| India | `RELIANCE.NS`, `RELIANCE.BO` |
| Canada | `SHOP.TO` |
| Australia | `BHP.AX` |
| China A-shares | `600519.SS`, `000001.SZ` |
| Crypto | `BTC-USD`, `ETH-USD` |
Broker-style symbols are normalized to Yahoo's convention automatically:

`XAUUSD` → `GC=F`, `BTCUSD` → `BTC-USD`, `EURUSD` → `EURUSD=X`,

`SPX500` → `^GSPC`, `09992.HK` → `9992.HK`, `600519.SH` → `600519.SS`.

---

## A note on what this is not

`tradeagents` is a research framework. It runs large language models over

financial data, produces reasoning you can read, and tracks whether that

reasoning held up. It is not:

- a trading system (there is no execution, no order management, no ledger)

- a portfolio simulator (backtest measures decision quality, not returns)

- investment advice

- a guarantee of anything

The interesting artifact is not the rating. It is the transcript — four

analysts, two debates, and a decision, each grounded in tool output with

citations. Read the debate before you read the decision.

---

## License

Apache 2.0. See `LICENSE`.

## Acknowledgments

Built on the shoulders of [LangGraph](https\://github.com/langchain-ai/langgraph)

for orchestration, [yfinance](https\://github.com/ranaroussi/yfinance) for

price data, [stockstats](https\://github.com/jealous/stockstats) for technical

indicators, and [Rich](https\://github.com/Textualize/rich) for the terminal

display. Data provided by Yahoo Finance, Alpha Vantage, the Federal Reserve

Bank of St. Louis (FRED), the U.S. Securities and Exchange Commission (EDGAR),

Polymarket, StockTwits, and Reddit.
