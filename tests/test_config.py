import pytest

from tradeagents import default_config as dc
from tradeagents.dataflows.config import get_config, set_config

# ---- _coerce: pure function, no env-var manipulation needed ----


@pytest.mark.unit
def test_coerce_bool_true_variants():
    for s in ("true", "1", "yes", "on", "TRUE", " Yes "):
        assert dc._coerce(s, False) is True


@pytest.mark.unit
def test_coerce_bool_false_variants():
    for s in ("false", "0", "no", "off", "NO"):
        assert dc._coerce(s, True) is False


@pytest.mark.unit
def test_coerce_bool_rejects_garbage():
    with pytest.raises(ValueError, match="boolean"):
        dc._coerce("maybe", True)


@pytest.mark.unit
def test_coerce_int_and_float():
    assert dc._coerce("42", 0) == 42
    assert dc._coerce("0.5", 0.0) == 0.5


@pytest.mark.unit
def test_coerce_str_passthrough():
    assert dc._coerce("hello", "world") == "hello"


# ---- _apply_env_overrides: the mechanism, in isolation ----


@pytest.mark.unit
def test_apply_env_overrides_coerces_types(monkeypatch):
    monkeypatch.setenv("TRADEAGENTS_MAX_DEBATE_ROUNDS", "3")
    monkeypatch.setenv("TRADEAGENTS_CHECKPOINT_ENABLED", "true")
    config = {"max_debate_rounds": 1, "checkpoint_enabled": False}
    dc._apply_env_overrides(config)
    assert config["max_debate_rounds"] == 3
    assert config["checkpoint_enabled"] is True


@pytest.mark.unit
def test_apply_env_overrides_ignores_empty(monkeypatch):
    monkeypatch.setenv("TRADEAGENTS_LLM_PROVIDER", "")
    config = {"llm_provider": "openai"}
    dc._apply_env_overrides(config)
    assert config["llm_provider"] == "openai"


# ---- get_config / set_config ----


@pytest.mark.unit
def test_get_config_returns_defaults():
    cfg = get_config()
    assert cfg["llm_provider"] == "openai"
    assert cfg["max_debate_rounds"] == 1


@pytest.mark.unit
def test_get_config_returns_a_copy():
    a = get_config()
    a["llm_provider"] = "mutated"
    assert get_config()["llm_provider"] != "mutated"


@pytest.mark.unit
def test_set_config_merges_nested_dicts():
    set_config({"data_vendors": {"core_stock_apis": "alpha_vantage"}})
    cfg = get_config()
    # Overridden key changed...
    assert cfg["data_vendors"]["core_stock_apis"] == "alpha_vantage"
    # ...while its sibling category defaults survived the merge.
    assert cfg["data_vendors"]["technical_indicators"] == "yfinance"
