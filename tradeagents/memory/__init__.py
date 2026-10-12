"""Memory: the decision log and the settlement that turns it into lessons.

Two concerns, one package:

  * ``log``        — append-only JSONL of every decision the pipeline produced.
  * ``settlement`` — once a decision's holding window has traded, fetch the
                     outcome, generate a reflection, and mark the entry settled.

The log is also the feedback channel: a later run for the same ticker reads its
settled entries as ``past_context``, so a run learns from what its own earlier
runs got right and wrong.
"""

from __future__ import annotations

from tradeagents.memory.log import DecisionLog
from tradeagents.memory.settlement import settle_pending

__all__ = ["DecisionLog", "settle_pending"]
