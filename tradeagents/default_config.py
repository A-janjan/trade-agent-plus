"""Default configuration and the single source of truth for env-var overrides.

Every key settable from the environment is registered in ``_ENV_OVERRIDES``.
Coercion is driven by the type of the existing default, so users can write
plain strings in `.env` and still get ints/bools/floats in the config dict.
"""

from __future__ import annotations

import os

_TRADEAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradeagents")

# env-var -> config-key. To expose a new key for env override, add a row here.
_ENV_OVERRIDES = {
    "TRADEAGENTS_LLM_PROVIDER": "llm_provider",
    "TRADEAGENTS_DEEP_THINK_LLM": "deep_think_llm",
    "TRADEAGENTS_QUICK_THINK_LLM": "quick_think_llm",
    "TRADEAGENTS_BACKEND_URL": "backend_url",
    "TRADEAGENTS_OUTPUT_LANGUAGE": "output_language",
    "TRADEAGENTS_MAX_DEBATE_ROUNDS": "max_debate_rounds",
    "TRADEAGENTS_MAX_RISK_ROUNDS": "max_risk_discuss_rounds",
    "TRADEAGENTS_CHECKPOINT_ENABLED": "checkpoint_enabled",
    "TRADEAGENTS_TEMPERATURE": "temperature",
}

_BOOL_TRUE = ("true", "1", "yes", "on")
_BOOL_FALSE = ("false", "0", "no", "off")


def _coerce(value: str, reference):
    """Coerce an env string to the type of ``reference`` (the current default).

    Invalid values raise rather than silently falling back — a misspelled
    boolean in an unattended run should fail loudly at startup, not quietly
    misconfigure the run.
    """
    if isinstance(reference, bool):
        v = value.strip().lower()
        if v in _BOOL_TRUE:
            return True
        if v in _BOOL_FALSE:
            return False
        raise ValueError(
            f"expected a boolean ({'/'.join(_BOOL_TRUE + _BOOL_FALSE)}), got {value!r}"
        )
    if isinstance(reference, int):
        return int(value)
    if isinstance(reference, float):
        return float(value)
    return value


def _apply_env_overrides(config: dict) -> dict:
    for env_var, key in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None or raw == "":
            continue
        try:
            config[key] = _coerce(raw, config.get(key))
        except ValueError as exc:
            raise ValueError(f"Invalid value for {env_var}: {exc}") from exc
    return config


DEFAULT_CONFIG = _apply_env_overrides(
    {
        # Storage
        "results_dir": os.getenv("TRADEAGENTS_RESULTS_DIR")
        or os.path.join(_TRADEAGENTS_HOME, "logs"),
        "data_cache_dir": os.getenv("TRADEAGENTS_CACHE_DIR")
        or os.path.join(_TRADEAGENTS_HOME, "cache"),
        # LLM
        "llm_provider": "openai",
        "deep_think_llm": "gpt-4o",
        "quick_think_llm": "gpt-4o-mini",
        "backend_url": None,
        "temperature": None,
        # Run behavior
        "checkpoint_enabled": False,
        "output_language": "English",
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
        "max_recur_limit": 100,  # The maximum recursion depth for the analyst graph. This is a safety limit to prevent infinite loops in the graph.
        # Vendors: category-level defaults. Populated as vendors land in Phase 2+.
        "data_vendors": {
            "core_stock_apis": "yfinance",
            "technical_indicators": "yfinance",
            "fundamental_data": "yfinance",
            "news_data": "yfinance",
        },
        # Tool-level overrides take precedence over category-level.
        "tool_vendors": {},
        # News and macro
        "news_article_limit": 20,
        "global_news_article_limit": 10,
        "global_news_lookback_days": 7,
        "global_news_queries": [
            "Federal Reserve interest rates inflation",
            "S&P 500 earnings GDP economic outlook",
            "geopolitical risk trade war sanctions",
            "ECB Bank of England BOJ central bank policy",
            "oil commodities supply chain energy",
        ],
    }
)
