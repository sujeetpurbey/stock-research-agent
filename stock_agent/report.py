"""Produce source-labelled, reproducible research artifacts."""
from __future__ import annotations

from datetime import datetime
from typing import Any


def fmt(value: float | None, spec: str) -> str:
    return format(value, spec) if value is not None else "N/A"


def render_markdown(rows: list[dict[str, Any]], errors: dict[str, str], generated: datetime, top: int = 10) -> str:
    ordered = sorted(rows, key=lambda x: (x["rating"] != "Research candidate", x["rating"] != "Watchlist", -x["score"]))
    picks = [r for r in ordered if r["rating"] in ("Research candidate", "Watchlist")][:top]
    lines = [
        "# Indian equity research screening report",
        "",
        f"Generated: {generated.isoformat()} | Data provider: Yahoo Finance via yfinance (unofficial, may be incomplete/delayed).",
        "",
        "**Important:** These are rule-based *research candidates*, not instructions to buy or sell. "
        "Scores are unvalidated heuristics, not return forecasts or probabilities. "
        "No trading, portfolio sizing or price targets are provided. Verify NSE/BSE filings and company reports before investing.",
        "",
        "## Screened stocks",
        "",
        "| Stock | Screen | Score / 100 | Last close | P/E | ROE | 6m return | Evidence date |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in ordered:
        lines.append(
            f'| {r["symbol"]} | {r["rating"]} | {r["score"]} | '
            f'{r["currency"]} {r["price"]:,.2f} | {fmt(r["trailing_pe"], ".1f")} | '
            f'{fmt(r["return_on_equity"], ".1%")} | {r["return_6m"]:+.1%} | {r["as_of"]} |'
        )
    lines += ["", "## Top research candidates", ""]
    if not picks:
        lines += ["None passed the minimum data/score checks. No positive stock candidate is issued.", ""]
    for i, r in enumerate(picks, 1):
        c = r["components"]
        lines += [
            f'### {i}. {r["name"]} ({r["symbol"]}) — {r["rating"]}, {r["score"]}/100',
            "",
            f'**Evidence:** {"; ".join(r["evidence"])}.',
            f'**Breakdown:** quality {c["quality"]}/35, growth {c["growth"]}/25, valuation {c["valuation"]}/20, momentum {c["momentum"]}/20. '
            f'Fundamental coverage: {r["fundamental_fields_available"]}/6 ({r["confidence"]}).',
            f'**Risks / gaps:** {"; ".join(r["risks"]) if r["risks"] else "No predefined screen flags; other risks remain."}',
            "",
        ]
    if errors:
        lines += ["## Symbols not analyzed", ""]
        for s, reason in errors.items():
            lines.append(f"- `{s}`: {reason}")
        lines.append("")
    lines += [
        "## Method and important limitations", "",
        "- 100-point heuristic: business quality (35), annual/quarterly growth snapshots as reported by the data vendor (25), "
        "simplified sector-aware P/E and P/B thresholds (20), and 50/200-day/6-month price momentum (20).",
        "- Financials are treated differently for valuation and debt, but financial-sector comparability is still limited.",
        "- The source's growth periods and field definitions may vary by ticker. No historical point-in-time fundamentals are collected.",
        "- Price history is adjusted for corporate actions and is end-of-day, not a real-time quotation.",
        "- Excludes forensic accounting, management quality, capital allocation, regulatory actions, insider trading, "
        "cash-flow review, catalysts and portfolio correlation. Quality of the underlying data is not independently verified.",
        "- Missing >=3 fundamental fields or stale prices (over 7 calendar days) block positive ratings.",
        "- For personal research only. If distributed as paid/personalized investment research, examine applicable SEBI requirements.",
        "",
    ]
    return "\n".join(lines)
