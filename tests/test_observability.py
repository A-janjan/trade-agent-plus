from __future__ import annotations

import pytest

from tradeagents.observability import (
    build_callbacks,
    langfuse_enabled,
    trace_metadata,
)


@pytest.fixture(autouse=True)
def _clear_langfuse_env(monkeypatch):
    for var in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.unit
def test_disabled_by_default_without_credentials():
    assert langfuse_enabled(None) is False
    assert build_callbacks({}) == []


@pytest.mark.unit
def test_auto_enables_when_both_credentials_present(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-x")
    assert langfuse_enabled({"langfuse": "auto"}) is True


@pytest.mark.unit
def test_auto_stays_off_with_only_one_credential(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-x")
    # Secret key absent; a half-configured client would fail on every request.
    assert langfuse_enabled({"langfuse": "auto"}) is False


@pytest.mark.unit
def test_explicit_off_overrides_credentials(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-x")
    assert langfuse_enabled({"langfuse": "off"}) is False
    assert build_callbacks({"langfuse": "off"}) == []


@pytest.mark.unit
def test_explicit_on_raises_without_credentials():
    with pytest.raises(ValueError, match="langfuse='on'"):
        langfuse_enabled({"langfuse": "on"})


@pytest.mark.unit
def test_unknown_mode_falls_back_to_auto(monkeypatch):
    # A typo in the config should not silently disable tracing; auto-detection
    # is the safe default.
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-x")
    assert langfuse_enabled({"langfuse": "tru"}) is True


@pytest.mark.unit
def test_build_callbacks_is_empty_without_langfuse_installed(monkeypatch):
    # Even with credentials set, a missing package must not raise — it logs and
    # returns [] so the pipeline runs untraced.
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-x")
    monkeypatch.setattr("tradeagents.observability._handler_class", lambda: None)
    assert build_callbacks({"langfuse": "auto"}) == []


@pytest.mark.unit
def test_trace_metadata_sets_langfuse_keys():
    meta = trace_metadata("NVDA", "2026-09-01", session_id="NVDA", tags=["t"])
    assert meta["run_name"] == "tradeagents · NVDA · 2026-09-01"
    assert meta["langfuse_session_id"] == "NVDA"
    assert meta["langfuse_tags"] == ["t"]
    assert meta["ticker"] == "NVDA"


@pytest.mark.unit
def test_trace_metadata_defaults_tags_from_asset_type():
    meta = trace_metadata("BTC-USD", "2026-09-01", asset_type="crypto")
    assert meta["langfuse_tags"] == ["tradeagents", "crypto"]
    assert "langfuse_session_id" not in meta


@pytest.mark.unit
def test_flush_is_safe_without_langfuse(monkeypatch):
    monkeypatch.setattr("tradeagents.observability._handler_class", lambda: None)
    from tradeagents.observability import flush

    flush()  # must not raise
