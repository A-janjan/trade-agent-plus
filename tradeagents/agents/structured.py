"""Structured-output helpers with a graceful free-text fallback.

Two factories and two call helpers cover every structured-output agent in the
system. Each factory wraps the LLM with ``with_structured_output(Schema)``; if
the provider doesn't support it, the wrap is skipped and the agent uses
free-text generation instead. At invocation, the structured call is attempted
first, then rendered back to markdown — on any failure (weak model, provider
hiccup, thinking model that answers in prose), the agent falls back to a plain
``invoke`` so the pipeline never blocks.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


# Schema-bound structured output attaches a single synthetic tool — the schema
# itself. A model that reaches for a real tool (search, fetch) emits an unknown
# tool call and the whole structured attempt is discarded for a free-text
# retry, which is worse than not trying. Structured-output agents without tools
# state the constraint in the prompt rather than relying on the binding alone.
NO_EXTERNAL_TOOLS = (
    "Use only the evidence provided in this prompt. Do not call external tools "
    "or search the web; if something is missing, say so explicitly."
)


def bind_structured(llm: Any, schema: type[T], agent_name: str) -> Any | None:
    """Return ``llm.with_structured_output(schema)`` or None if unsupported."""
    try:
        return llm.with_structured_output(schema)
    except (NotImplementedError, AttributeError) as exc:
        logger.warning(
            "%s: provider does not support with_structured_output (%s); "
            "falling back to free-text generation",
            agent_name,
            exc,
        )
        return None


def invoke_structured_or_freetext(
    structured_llm: Any | None,
    plain_llm: Any,
    prompt: Any,
    render: Callable[[T], str],
    agent_name: str,
) -> str:
    """Run the structured call and render to markdown; fall back to free text.

    A thinking model can answer in prose instead of calling the schema tool,
    leaving the parser with nothing; that is treated as a structured miss and
    falls through to the free-text path.
    """
    if structured_llm is not None:
        try:
            result = structured_llm.invoke(prompt)
            if result is None:
                raise ValueError("structured output returned no parsed result")
            return render(result)
        except Exception as exc:
            logger.warning(
                "%s: structured-output invocation failed (%s); retrying as free text",
                agent_name,
                exc,
            )
    return plain_llm.invoke(prompt).content
