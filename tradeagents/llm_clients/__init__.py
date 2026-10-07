"""LLM client factory.

Phase 3 supports OpenAI only; the factory structure is provider-agnostic so
adding a provider later is a new branch, not a rewrite.
"""

from __future__ import annotations

from typing import Any

from tradeagents.llm_clients.openai_client import create_openai_llm

__all__ = ["create_llm"]


def create_llm(config: dict, mode: str = "quick", *, streaming: bool = False) -> Any:
    """Return a chat model for ``config`` and ``mode`` ('quick' or 'deep')."""
    provider = (config.get("llm_provider") or "openai").lower()
    model_key = "quick_think_llm" if mode == "quick" else "deep_think_llm"
    model = config.get(model_key)
    if not model:
        raise ValueError(f"No model configured for {model_key!r}")

    if provider == "openai":
        return create_openai_llm(model, config, streaming=streaming)

    raise ValueError(f"Provider {provider!r} is not yet supported.")
