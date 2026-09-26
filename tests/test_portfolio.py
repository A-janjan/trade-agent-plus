import pytest

from tradeagents.portfolio import PortfolioContext, load_portfolio


@pytest.mark.unit
def test_render_flat_book():
    p = PortfolioContext(cash=10_000, currency="USD")
    text = p.render("NVDA")
    assert "No current position in NVDA" in text
    assert "10,000.00 USD" in text


@pytest.mark.unit
def test_render_with_position():
    p = PortfolioContext.model_validate(
        {
            "cash": 5_000.0,
            "currency": "USD",
            "positions": [{"ticker": "NVDA", "quantity": 120, "average_price": 150.0}],
        }
    )
    text = p.render("NVDA")
    assert "120 units" in text
    assert "average price 150.00" in text
    assert "5,000.00 USD" in text


@pytest.mark.unit
def test_render_lists_other_positions():
    p = PortfolioContext.model_validate(
        {
            "positions": [
                {"ticker": "NVDA", "quantity": 120},
                {"ticker": "AAPL", "quantity": 30},
            ],
        }
    )
    text = p.render("NVDA")
    assert "Other positions: AAPL 30" in text


@pytest.mark.unit
def test_position_in_is_case_insensitive():
    p = PortfolioContext.model_validate(
        {
            "positions": [{"ticker": "NVDA", "quantity": 1}],
        }
    )
    assert p.position_in("nvda") is not None
    assert p.position_in("AAPL") is None


@pytest.mark.unit
def test_fingerprint_changes_with_book():
    assert (
        PortfolioContext(cash=1).fingerprint() != PortfolioContext(cash=2).fingerprint()
    )


@pytest.mark.unit
def test_fingerprint_is_stable_for_same_book():
    a = PortfolioContext(cash=1_000, positions=[])
    b = PortfolioContext(cash=1_000, positions=[])
    assert a.fingerprint() == b.fingerprint()


@pytest.mark.unit
def test_load_portfolio_missing_file(tmp_path):
    with pytest.raises(ValueError, match="not usable"):
        load_portfolio(tmp_path / "missing.json")


@pytest.mark.unit
def test_load_portfolio_rejects_malformed(tmp_path):
    f = tmp_path / "book.json"
    f.write_text('{"positions": [{"quantity": "not a number"}]}', encoding="utf-8")
    with pytest.raises(ValueError, match="not usable"):
        load_portfolio(f)
