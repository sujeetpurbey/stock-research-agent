"""Fetch Yahoo Finance evidence, calculate transparent stock research scores."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from math import isfinite, sqrt
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

IST = ZoneInfo("Asia/Kolkata")
FINANCIAL_SECTORS = {"financial services", "financials"}


def number(value: Any) -> float | None:
    """Accept only finite numeric data (bool, infinity, blanks are invalid)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (TypeError, ValueError):
        return None


@dataclass
class Snapshot:
    symbol: str
    name: str
    sector: str
    as_of: str
    currency: str
    price: float
    sma50: float
    sma200: float
    return_6m: float
    drawdown_52w: float
    annual_volatility: float
    trailing_pe: float | None = None
    price_to_book: float | None = None
    return_on_equity: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    profit_margin: float | None = None
    debt_to_equity: float | None = None  # normalized decimal; Yahoo value /100
    market_cap: float | None = None


def fetch_snapshot(symbol: str) -> Snapshot:
    """Download data on demand. Prices are adjusted. Does NOT return live intraday quotes."""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2y", interval="1d", auto_adjust=True)
    if hist.empty or "Close" not in hist:
        raise ValueError("No daily price history from Yahoo Finance")
    close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
    if len(close) < 210:
        raise ValueError(f"Only {len(close)} usable closes; require >=210")
    if close.iloc[-1] <= 0:
        raise ValueError("Nonpositive latest close")
    as_of = close.index[-1].date().isoformat()
    daily = close.pct_change(fill_method=None).dropna()
    annual_volatility = float(daily.tail(252).std(ddof=1) * sqrt(252))
    try:
        info = ticker.info or {}
    except Exception:
        info = {}
    price = float(close.iloc[-1])
    return Snapshot(
        symbol=symbol,
        name=str(info.get("shortName") or info.get("longName") or symbol),
        sector=str(info.get("sector") or "Unknown"),
        as_of=as_of,
        currency=str(info.get("currency") or ("INR" if symbol.endswith(".NS") or symbol.endswith(".BO") else "Unknown")),
        price=price,
        sma50=float(close.tail(50).mean()),
        sma200=float(close.tail(200).mean()),
        return_6m=price / float(close.iloc[-127]) - 1,
        drawdown_52w=price / float(close.tail(252).max()) - 1,
        annual_volatility=annual_volatility,
        trailing_pe=number(info.get("trailingPE")),
        price_to_book=number(info.get("priceToBook")),
        return_on_equity=number(info.get("returnOnEquity")),
        revenue_growth=number(info.get("revenueGrowth")),
        earnings_growth=number(info.get("earningsGrowth")),
        profit_margin=number(info.get("profitMargins")),
        debt_to_equity=(number(info.get("debtToEquity")) / 100 if number(info.get("debtToEquity")) is not None else None),
        market_cap=number(info.get("marketCap")),
    )


def score_snapshot(s: Snapshot, now: datetime | None = None) -> dict[str, Any]:
    """Heuristic rank, not a probability, forward return, or target price.

    100 points maximum: quality 35, growth 25, valuation 20, momentum 20.
    Missing or stale data prevents a positive research rating.
    """
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=IST)
    asof_date = datetime.fromisoformat(s.as_of).date()
    stale = (now.date() - asof_date) > timedelta(days=7) or asof_date > now.date()
    financial = s.sector.strip().lower() in FINANCIAL_SECTORS

    fundamentals = [s.trailing_pe, s.price_to_book, s.return_on_equity,
                    s.revenue_growth, s.earnings_growth, s.profit_margin]
    available = sum(x is not None for x in fundamentals)

    quality = 0
    if s.return_on_equity is not None:
        quality += 15 if s.return_on_equity >= .20 else 10 if s.return_on_equity >= .15 else 6 if s.return_on_equity >= .10 else 0
    if s.profit_margin is not None:
        quality += 10 if s.profit_margin >= .20 else 7 if s.profit_margin >= .10 else 4 if s.profit_margin >= .05 else 0
    if financial:
        quality += 5
    elif s.debt_to_equity is not None:
        quality += 10 if s.debt_to_equity < .30 else 7 if s.debt_to_equity < .80 else 3 if s.debt_to_equity < 1.50 else 0

    growth = 0
    if s.revenue_growth is not None:
        growth += 12 if s.revenue_growth >= .20 else 9 if s.revenue_growth >= .10 else 6 if s.revenue_growth >= .05 else 3 if s.revenue_growth > 0 else 0
    if s.earnings_growth is not None:
        growth += 13 if s.earnings_growth >= .20 else 10 if s.earnings_growth >= .10 else 6 if s.earnings_growth > 0 else 0

    valuation = 0
    if s.trailing_pe is not None and s.trailing_pe > 0:
        if financial:
            valuation += 12 if s.trailing_pe <= 12 else 10 if s.trailing_pe <= 18 else 6 if s.trailing_pe <= 25 else 2 if s.trailing_pe <= 35 else 0
        else:
            valuation += 12 if s.trailing_pe <= 15 else 10 if s.trailing_pe <= 25 else 5 if s.trailing_pe <= 40 else 0
    if s.price_to_book is not None and s.price_to_book > 0:
        if financial:
            valuation += 8 if s.price_to_book <= 1.5 else 6 if s.price_to_book <= 2.5 else 3 if s.price_to_book <= 4 else 0
        else:
            valuation += 8 if s.price_to_book <= 2 else 5 if s.price_to_book <= 4 else 2 if s.price_to_book <= 8 else 0

    momentum = 0
    momentum += 8 if s.price >= s.sma200 else 0
    momentum += 4 if s.price >= s.sma50 else 0
    momentum += 8 if s.return_6m >= .20 else 5 if s.return_6m >= .05 else 3 if s.return_6m > 0 else 0
    if s.drawdown_52w < -.35:
        momentum = max(0, momentum - 5)
    if s.annual_volatility > .60:
        momentum = max(0, momentum - 3)

    risks = []
    if s.price < s.sma200:
        risks.append("Price below 200-day average")
    if s.drawdown_52w < -.30:
        risks.append("More than 30% below 52-week peak")
    if s.annual_volatility > .60:
        risks.append("Annualized daily-return volatility above 60%")
    if s.earnings_growth is not None and s.earnings_growth < -.10:
        risks.append("Earnings growth below -10%")
    if s.return_on_equity is not None and s.return_on_equity < 0:
        risks.append("Negative return on equity")
    if not financial and s.debt_to_equity is not None and s.debt_to_equity > 1.50:
        risks.append("Debt/equity above 1.5x")
    if s.trailing_pe is not None and s.trailing_pe > (35 if financial else 45):
        risks.append("High P/E by simplified sector heuristic")
    if available < 5:
        risks.append("Limited fundamental-data coverage")
    if stale:
        risks.append("Price data older than 7 days or future-dated")

    total = min(100, quality + growth + valuation + momentum)
    high_concern = (s.return_on_equity is not None and s.return_on_equity < 0) or (
        s.earnings_growth is not None and s.earnings_growth < -.30
    )
    if stale:
        label = "Stale data"
    elif available < 4:
        label = "Insufficient data"
    elif high_concern:
        label = "Low priority"
    elif total >= 75:
        label = "Research candidate"
    elif total >= 55:
        label = "Watchlist"
    else:
        label = "Low priority"

    return {
        **asdict(s),
        "score": total,
        "components": {"quality": quality, "growth": growth, "valuation": valuation, "momentum": momentum},
        "rating": label,
        "fundamental_fields_available": available,
        "confidence": "Higher" if available >= 6 else "Moderate" if available >= 4 else "Low",
        "risks": risks,
        "evidence": [
            f"ROE {s.return_on_equity:.1%}" if s.return_on_equity is not None else "ROE unavailable",
            f"Revenue growth {s.revenue_growth:+.1%}" if s.revenue_growth is not None else "Revenue growth unavailable",
            f"6-month price return {s.return_6m:+.1%}",
            "Above 200-day trend" if s.price >= s.sma200 else "Below 200-day trend",
        ],
    }
