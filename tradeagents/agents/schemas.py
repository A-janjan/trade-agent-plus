"""Pydantic schemas for structured analyst output.

Structured output is layered where machine-readable fields genuinely help:
the sentiment analyst's band + score + confidence are read by downstream
consumers, so they are typed. Prose reports (market, fundamentals, news) stay
free text.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


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
