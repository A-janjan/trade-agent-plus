"""
real name: Historical Decision Evaluation

Score a backtest's decision log, by rating.

The log is the results table. Every statistic here comes from reading it; there
is no parallel record that could drift from what the pipeline actually decided.
An entry counts toward a rating's figures only once it has settled (its holding
window has traded). Pending entries are reported separately, never silently
folded into a rating's mean.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tradeagents.backtest.runner import BacktestResult
from tradeagents.memory.log import DecisionLog
from tradeagents.memory.rating import RATING_REVIEW

# What each rating claims will happen. Hold claims no direction, so nothing
# about the realized return proves it right or wrong — hit rate is undefined
# for Hold, not zero.
_DIRECTION: dict[str, int] = {
    "Strong Buy": 1,
    "Buy": 1,
    "Hold": 0,
    "Sell": -1,
    "Strong Sell": -1,
}

# The order ratings appear in a summary, most bullish first. Any rating not
# listed (a future addition) sorts last so nothing is dropped from the report.
_ORDER = ("Strong Buy", "Buy", "Hold", "Sell", "Strong Sell")


@dataclass
class RatingScore:
    """Per-rating statistics: count, directional hit rate, mean alpha."""

    count: int
    mean_alpha: float
    hit_rate: float | None  # None for Hold (no direction claimed)


@dataclass
class BacktestSummary:
    """The full aggregate over a backtest's resolved cells."""

    resolved: int
    pending: int
    unscored: int
    by_rating: dict[str, RatingScore]
    holding: str  # e.g. "5 trading days"

    def render(self) -> str:
        """A human-readable multi-line summary."""
        lines = [
            f"Resolved cells: {self.resolved} · "
            f"pending: {self.pending} · "
            f"unscored: {self.unscored}",
            "",
        ]
        if self.by_rating:
            for rating in _sort_keys(self.by_rating):
                s = self.by_rating[rating]
                direction = (
                    f"called direction {s.hit_rate:.0%}"
                    if s.hit_rate is not None
                    else "no direction claimed"
                )
                lines.append(
                    f"  {rating}: n={s.count}, {direction}, "
                    f"mean alpha {s.mean_alpha:+.2%}"
                )
        else:
            lines.append("  (no resolved cells)")
        lines.append("")
        if self.pending:
            lines.append("Pending cells are not scored above; re-run to settle them.")
        if self.unscored:
            lines.append(
                f"Unscored cells ({self.unscored}) produced no parseable rating; "
                "they neither count for nor against the system."
            )
        lines.append(
            f"Alpha is realized over {self.holding} after each analysis date. "
            "One model sampling per cell, and live text feeds are not archived, "
            "so these figures are indicative rather than repeatable."
        )
        return "\n".join(lines)


def _sort_keys(by_rating: dict[str, RatingScore]) -> list[str]:
    """Ratings in bull-to-bear order; unknown keys (future additions) sort last."""
    known = [r for r in _ORDER if r in by_rating]
    unknown = sorted(k for k in by_rating if k not in _ORDER)
    return known + unknown


def _alpha_percent(entry: dict) -> float | None:
    """Read the settled alpha off an entry.

    Settlement stores alpha as a float; a legacy entry might carry a percentage
    string. Accept both rather than dropping either silently.
    """
    value = entry.get("alpha_return")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.endswith("%"):
        try:
            return float(value.rstrip("%")) / 100
        except ValueError:
            return None
    return None


def _holding_label(entries: list[dict]) -> str:
    """The measured holding window, taken from the entries themselves.

    Different entries could in principle be resolved under different windows
    if a config changed mid-sweep; naming them all is more honest than
    picking one.
    """
    days = {
        int(e["holding_days"]) for e in entries if e.get("holding_days") is not None
    }
    if not days:
        return "the configured window"
    if len(days) == 1:
        return f"{days.pop()} trading days"
    return f"{', '.join(str(d) for d in sorted(days))} trading days"


def _load_entries(source: BacktestResult | str | Path) -> list[dict]:
    """Read the decision log a summary is being built from.

    A missing file is a caller error — the log a summary is asked to score
    does not exist. An existing file with zero entries is a legitimate state
    and summarizes to zero.
    """
    path = source.log_path if isinstance(source, BacktestResult) else Path(source)
    if not path.exists():
        raise FileNotFoundError(f"no decision log at {path}")
    return DecisionLog(path).all_entries()


def summarize(source: BacktestResult | str | Path) -> BacktestSummary:
    """Score a backtest's settled cells, grouped by rating."""
    entries = _load_entries(source)

    # A decision with no readable rating has no direction, so it can neither
    # count for nor against the system; it is reported separately.
    resolved = [
        e
        for e in entries
        if e.get("settled")
        and e.get("rating") != RATING_REVIEW
        and _alpha_percent(e) is not None
    ]
    pending = sum(1 for e in entries if not e.get("settled"))
    unscored = sum(
        1
        for e in entries
        if e.get("settled")
        and (e.get("rating") == RATING_REVIEW or _alpha_percent(e) is None)
    )

    by_rating: dict[str, RatingScore] = {}
    for rating in dict.fromkeys(e["rating"] for e in resolved):
        alphas = [_alpha_percent(e) for e in resolved if e["rating"] == rating]
        alphas = [
            a for a in alphas if a is not None
        ]  # mypy: filtered above, cheap here
        direction = _DIRECTION.get(rating, 0)
        by_rating[rating] = RatingScore(
            count=len(alphas),
            mean_alpha=sum(alphas) / len(alphas),
            hit_rate=(
                sum(1 for a in alphas if a * direction > 0) / len(alphas)
                if direction and alphas
                else None
            ),
        )

    return BacktestSummary(
        resolved=len(resolved),
        pending=pending,
        unscored=unscored,
        by_rating=by_rating,
        holding=_holding_label(resolved),
    )
