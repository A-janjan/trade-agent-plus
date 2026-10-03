"""OpenAI chat model construction."""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI


def create_openai_llm(model: str, config: dict) -> ChatOpenAI:
    """Build a ``ChatOpenAI`` from config, with a clear error when the key is absent."""
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
    return ChatOpenAI(**kwargs)
