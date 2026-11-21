from datetime import datetime
from zoneinfo import ZoneInfo

from stock_agent.cli import parse_symbols
from stock_agent.engine import Snapshot, number, score_snapshot
from stock_agent.report import render_markdown

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata"))


def sample(**kwargs):
    base = dict(
        symbol="DEMO.NS", name="Demo Co", sector="Technology", as_of="2026-11-20",
        currency="INR", price=200, sma50=180, sma200=150,
        return_6m=.30, drawdown_52w=-.05, annual_volatility=.23,
        trailing_pe=14, price_to_book=1.8, return_on_equity=.24,
        revenue_growth=.22, earnings_growth=.25, profit_margin=.21,
        debt_to_equity=.12, market_cap=100000000,
    )
    base.update(kwargs)
    return Snapshot(**base)


def test_strong_company_is_candidate():
    r = score_snapshot(sample(), NOW)
    assert r["score"] == 100
    assert r["rating"] == "Research candidate"
    assert r["components"] == {"quality": 35, "growth": 25, "valuation": 20, "momentum": 20}


def test_missing_fundamentals_never_recommended():
    r = score_snapshot(sample(trailing_pe=None, price_to_book=None, return_on_equity=None,
                              revenue_growth=None, earnings_growth=None, profit_margin=None), NOW)
    assert r["rating"] == "Insufficient data"
    assert r["confidence"] == "Low"


def test_stale_data_never_recommended():
    r = score_snapshot(sample(as_of="2026-11-01"), NOW)
    assert r["rating"] == "Stale data"
    assert any("older" in flag for flag in r["risks"])


def test_financial_debt_not_penalized_by_generic_rule():
    r = score_snapshot(sample(sector="Financial Services", debt_to_equity=10.0), NOW)
    assert not any("Debt/equity" in flag for flag in r["risks"])


def test_high_risk_earnings_prevent_candidate():
    r = score_snapshot(sample(earnings_growth=-.50), NOW)
    assert r["rating"] == "Low priority"


def test_symbol_parser_validates_and_dedupes():
    assert parse_symbols("INFY, INFY.NS\nAAPL\nBRK.B # US") == ["INFY.NS", "AAPL.NS", "BRK.B"]


def test_number_rejects_inf_bool():
    assert number(float("inf")) is None
    assert number(True) is None
    assert number("23.4") == 23.4


def test_reports_show_provider_and_unvalidated_caveat():
    r = score_snapshot(sample(), NOW)
    output = render_markdown([r], {}, NOW)
    assert "unofficial" in output
    assert "not return forecasts" in output
    assert "DEMO.NS" in output


def test_full_cli_creates_evidence_report_without_network(tmp_path, monkeypatch):
    from stock_agent import cli
    monkeypatch.setattr(cli, "fetch_snapshot", lambda symbol: sample(symbol=symbol))
    assert cli.main(["--symbols", "DEMO", "--output-dir", str(tmp_path)]) == 0
    md_files = list(tmp_path.glob("*.md"))
    json_files = list(tmp_path.glob("*.json"))
    assert len(md_files) == len(json_files) == 1
    assert "Research candidate" in md_files[0].read_text()
    import json
    data = json.loads(json_files[0].read_text())
    assert data["rows"][0]["symbol"] == "DEMO.NS"
