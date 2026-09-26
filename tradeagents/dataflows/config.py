"""Process-wide config accessor.

The default config is immutable at the module level; this module serves a
mutable copy that callers can override per-process via ``set_config``.
Per-run scoping (so concurrent graphs don't race) comes in a later phase.
"""

from __future__ import annotations

from copy import deepcopy

import tradeagents.default_config as default_config

_config: dict | None = None


def initialize_config() -> None:
    global _config
    if _config is None:
        _config = deepcopy(default_config.DEFAULT_CONFIG)


def _merge(base: dict, overlay: dict) -> dict:
    """Merge ``overlay`` into ``base``: nested dicts one level deep, scalars replaced."""
    for key, value in deepcopy(overlay).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key].update(value)
        else:
            base[key] = value
    return base


def set_config(config: dict) -> None:
    """Update process-wide config. Nested dict keys merge one level deep."""
    initialize_config()
    assert _config is not None
    _merge(_config, config)


def get_config() -> dict:
    """Return a copy of the current config, so callers cannot mutate it in place."""
    initialize_config()
    assert _config is not None
    return deepcopy(_config)
