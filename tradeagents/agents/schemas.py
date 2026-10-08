"""Pydantic schemas for structured analyst output.

Structured output is layered where machine-readable fields genuinely help:
the sentiment analyst's band + score + confidence are read by downstream
consumers, so they are typed. Prose reports (market, fundamentals, news) stay
free text.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SentimentBand(StrEnum):
    """Six-tier sentiment direction: granular enough to act on, small enough
    that every provider maps it reliably."""

    BULLISH = "Bullish"
    MILDLY_BULLISH = "Mildly Bullish"
    NEUTRAL = "Neutral"
    MIXED = "Mixed"
    MILDLY_BEARISH = "Mildly Bearish"
    BEARISH = "Bearish"


class SentimentReport(BaseModel):
    """Structured sentiment report produced by the sentiment analyst."""

    overall_band: SentimentBand = Field(
        description=(
            "Overall sentiment direction. Exactly one of: Bullish / Mildly "
            "Bullish / Neutral / Mixed / Mildly Bearish / Bearish. Use Mixed "
            "when sources point in clearly different directions. Use Neutral "
            "only when all sources are genuinely silent."
        ),
    )
    overall_score: float = Field(
        ge=0.0,
        le=10.0,
        description=(
            "Numeric sentiment intensity 0-10. 0 = maximally bearish, 5 = "
            "neutral, 10 = maximally bullish. Keep consistent with band."
        ),
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description=(
            "Confidence in the read given data quality and sample size. 'low' "
            "if any source returned a placeholder or <5 data points; 'high' if "
            "all three sources returned substantive data."
        ),
    )
    narrative: str = Field(
        description=(
            "Full report covering, in order: (1) source-by-source breakdown "
            "with specific evidence; (2) cross-source divergences and "
            "alignments; (3) dominant narrative themes; (4) catalysts and "
            "risks; (5) a markdown summary table of key sentiment signals, "
            "their direction, source, and supporting evidence."
        ),
    )


def render_sentiment_report(report: SentimentReport) -> str:
    """Render a SentimentReport to the markdown shape the rest of the system consumes."""
    return "\n".join(
        [
            f"**Overall Sentiment:** **{report.overall_band.value}** "
            f"(Score: {report.overall_score:.1f}/10)",
            f"**Confidence:** {report.confidence.capitalize()}",
            "",
            report.narrative,
        ]
    )


class Stance(StrEnum):
    """Five-tier investment stance used by the research debate's verdict."""

    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"


class InvestmentPlan(BaseModel):
    """The Investment Lead's synthesized verdict and rationale."""

    stance: Stance = Field(
        description=(
            "Exactly one of Strong Buy / Buy / Hold / Sell / Strong Sell. "
            "The debate will contain conflicts; deciding which side is "
            "stronger is your job, so conflict alone is not a reason to Hold."
        ),
    )
    thesis: str = Field(
        description=(
            "Two to three paragraphs anchoring the stance in specific "
            "evidence from the debate and the analyst reports."
        ),
    )
    key_risks: list[str] = Field(
        description="Three to five concrete risks to the stance.",
    )
    catalysts: list[str] = Field(
        description="Two to four near-term events or developments to watch.",
    )
    conviction: Literal["low", "medium", "high"] = Field(
        description="How decisively the evidence supports the stance.",
    )


def render_investment_plan(plan: InvestmentPlan) -> str:
    """Render an InvestmentPlan to the markdown shape the rest of the system consumes."""
    risks = "\n".join(f"- {r}" for r in plan.key_risks) or "- none stated"
    catalysts = "\n".join(f"- {c}" for c in plan.catalysts) or "- none stated"
    return "\n".join(
        [
            f"**Stance**: {plan.stance.value}",
            f"**Conviction**: {plan.conviction.capitalize()}",
            "",
            "**Thesis**",
            plan.thesis,
            "",
            "**Key risks**",
            risks,
            "",
            "**Catalysts**",
            catalysts,
        ]
    )


class TraderAction(StrEnum):
    """Three-tier transaction direction used by the trader.

    The research lead's five-tier stance is mapped here, not carried through:
    the trader's job is to commit to what the desk does this round, and
    'Overweight' is not an order.
    """

    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"


# Placeholders a model writes in an optional numeric field instead of omitting
# it. Coerced to None so the structured call validates.
_NULLISH = {
    "",
    "none",
    "n/a",
    "na",
    "null",
    "nil",
    "-",
    "tbd",
    "unknown",
    "not provided",
}


def _coerce_price(value):
    """Normalize an LLM-written price field before validation.

    Three bad shapes show up in practice: a placeholder string in place of an
    omitted value; a percentage where a price was asked for; and a
    human-formatted price. A percentage cannot be salvaged — reading "15%"
    as 15 would put a stop at $15 on a $600 stock — so it is dropped like a
    placeholder. A formatted price is reduced to its number. Anything that is
    not a single number (a range, a hedge, an adjective) is dropped the same
    way, so one bad field nulls out instead of failing the whole proposal and
    losing every field the model got right.
    """
    if value is None or isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.lower() in _NULLISH or text.endswith("%"):
        return None
    cleaned = text.replace(",", "").lstrip("$€£¥").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


class TraderProposal(BaseModel):
    """The trader's transaction proposal.

    ``entry_price`` and ``stop_loss`` are optional: a Hold needs neither, and a
    market order needs no entry level. What is not optional is the *shape* —
    when a level is given, it is an absolute price, never a percentage.
    """

    action: TraderAction = Field(
        description="Exactly one of Buy / Hold / Sell.",
    )
    reasoning: str = Field(
        description=(
            "Two to four sentences: why this action, anchored in the "
            "investment plan and the market report's price structure."
        ),
    )
    entry_price: float | None = Field(
        default=None,
        description=(
            "Optional entry price as an absolute number in the instrument's "
            "quote currency (e.g. 189.5). Never a percentage or a range; omit "
            "if you cannot state a specific level."
        ),
    )
    stop_loss: float | None = Field(
        default=None,
        description=(
            "Optional stop-loss as an absolute price in the instrument's quote "
            "currency (e.g. 172.0). Never a percentage. Convert a percentage "
            "distance to the price level it implies, or omit it."
        ),
    )
    position_sizing: str | None = Field(
        default=None,
        description=(
            "Optional sizing guidance, e.g. '5% of portfolio', 'add 1% of "
            "current book'. When the caller's book was provided, size against "
            "it; when it was not, size against a standard allocation."
        ),
    )

    @field_validator("entry_price", "stop_loss", mode="before")
    @classmethod
    def _normalize_price(cls, v):
        return _coerce_price(v)


def render_trader_proposal(proposal: TraderProposal) -> str:
    """Render a TraderProposal to the markdown the report tree and CLI consume.

    Absent fields are named even when empty, so a reader can tell a level the
    trader chose not to give from a level the schema never asked for.
    """

    def show(value):
        return "not provided" if value is None or value == "" else value

    return "\n".join(
        [
            f"**Action**: {proposal.action.value}",
            "",
            f"**Reasoning**: {proposal.reasoning}",
            "",
            f"**Entry Price**: {show(proposal.entry_price)}",
            f"**Stop Loss**: {show(proposal.stop_loss)}",
            f"**Position Sizing**: {show(proposal.position_sizing)}",
        ]
    )
