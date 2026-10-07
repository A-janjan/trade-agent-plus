"""OpenAI chat model construction."""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI


def create_openai_llm(
    model: str, config: dict, *, streaming: bool = False
) -> ChatOpenAI:
    """Build a ``ChatOpenAI`` from config.

    ``streaming`` is forwarded to the SDK. It matters for the live display:
    without it, LangGraph's ``messages`` stream mode only sees the response
    once it is complete, so the preview would appear all at once at the end.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Export it, or add it to your .env file "
            "(see .env.example)."
        )

    kwargs: dict = {"model": model, "api_key": api_key}
    if config.get("backend_url"):
        kwargs["base_url"] = config["backend_url"]
    elif os.environ.get("OPENAI_BASE_URL"):
        kwargs["base_url"] = os.environ.get("OPENAI_BASE_URL")
    if config.get("temperature") is not None:
        kwargs["temperature"] = config["temperature"]
    if streaming:
        kwargs["streaming"] = True
    return ChatOpenAI(**kwargs)
