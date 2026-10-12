"""Fallback rating extraction from free-text decisions.

Used only when the PM's structured call did not run — a provider without
structured-output support, or a call that failed. When the structured path
succeeded, ``state["final_rating"]`` is authoritative and this is not called.
"""

from __future__ import annotations

import re
import unicodedata

RATINGS = ("Strong Buy", "Buy", "Hold", "Sell", "Strong Sell")
RATING_REVIEW = "REVIEW"

# "Rating: X" / "rating - X" / "Rating — **X**": tolerates bold wrappers and
# any dash or colon a model writes as the separator.
_LABEL = re.compile(
    r"rating\b[^:\-\u2010-\u2015]*[:\-\u2010-\u2015][\s*]*([A-Za-z ]+)",
    re.IGNORECASE,
)
# A line presenting the scale itself ("Rating Scale: Buy, ..."), which the
# model echoed as a legend rather than as a call.
_SCALE = re.compile(r"rating\s*(scale|options|legend)", re.IGNORECASE)
# Standalone five-tier phrase anywhere. Longest first so "Strong Buy" wins
# over "Buy" when both appear.
_WORD = re.compile(
    r"\b(" + "|".join(sorted(RATINGS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def extract_rating(text: str) -> str | None:
    """Extract a rating from prose, or None if none is present.

    Two passes over NFKC-normalized text (so ``Rating:Buy`` with a fullwidth
    colon works the same as ASCII):
      1. The labeled "Rating: X" form, taking the last match: a decision
         states its rating after discussing the alternatives, and the last one
         is the call.
      2. The first standalone rating phrase, if exactly one appears. Multiple
         phrases are an argument, not a call.
    """
    if not text:
        return None
    norm = unicodedata.normalize("NFKC", text)

    labeled: str | None = None
    for line in norm.splitlines():
        if _SCALE.search(line):
            continue
        m = _LABEL.search(line)
        if m:
            word = m.group(1).strip().rstrip("*").strip()
            for r in sorted(RATINGS, key=len, reverse=True):
                if word.lower().startswith(r.lower()):
                    labeled = r
                    break
    if labeled:
        return labeled

    matches = {_canonical(m.group(1)) for m in _WORD.finditer(norm)}
    return matches.pop() if len(matches) == 1 else None


def _canonical(word: str) -> str:
    return word.strip().title().replace("  ", " ")


def parse_rating(text: str) -> str:
    """Extract a rating, or ``REVIEW`` when the decision has none.

    REVIEW is not a tradeable rating: it flags output that needs a human or a
    re-run, rather than silently degrading to Hold, which would record a call
    nobody made.
    """
    return extract_rating(text) or RATING_REVIEW
