"""CLI for locally launched or scheduled research runs."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from stock_agent.ai import generate_narrative
from stock_agent.engine import fetch_snapshot, score_snapshot
from stock_agent.report import render_markdown

DEFAULT_UNIVERSE = Path(__file__).resolve().parent.parent / "config" / "watchlist.txt"
VALID_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.\-^]{0,24}$")


def parse_symbols(text: str) -> list[str]:
    result = []
    for line in text.replace(",", "\n").splitlines():
        value = line.split("#", 1)[0].strip().upper()
        if not value:
            continue
        if "." not in value and not value.startswith("^"):
            value += ".NS"
        if not VALID_SYMBOL.fullmatch(value):
            raise ValueError(f"Unsafe or unsupported symbol: {value}")
        if value not in result:
            result.append(value)
    if not result:
        raise ValueError("Supply at least one symbol")
    if len(result) > 50:
        raise ValueError("Limit is 50 tickers per run to reduce rate limits")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence-based India stock research screener")
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--symbols", help="comma-separated tickers, e.g. INFY,RELIANCE,HDFCBANK")
    src.add_argument("--symbols-file", type=Path, help="text file, ticker per line")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--ai-summary", action="store_true", help="append optional OpenAI evidence-only narrative")
    parser.add_argument("--model", help="OpenAI model name, when --ai-summary is enabled")
    args = parser.parse_args(argv)
    if args.top < 1 or args.top > 50:
        parser.error("--top must be between 1 and 50")
    try:
        symbols = parse_symbols(args.symbols if args.symbols is not None else (args.symbols_file or DEFAULT_UNIVERSE).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    rows, errors = [], {}
    for symbol in symbols:
        print(f"Analyzing {symbol}...", flush=True)
        try:
            rows.append(score_snapshot(fetch_snapshot(symbol), now=now))
        except Exception as exc:
            errors[symbol] = f"Data fetch failed ({type(exc).__name__}): {exc}"
            print(f"WARN {symbol}: {errors[symbol]}", file=sys.stderr)

    if not rows:
        print("ERROR: No valid stock data. Report not generated.", file=sys.stderr)
        return 2
    report = render_markdown(rows, errors, now, args.top)
    if args.ai_summary:
        try:
            report += "\n## Optional AI-written commentary (numbers unchanged)\n\n" + generate_narrative(
                sorted(rows, key=lambda x: -x["score"]), model=args.model
            ) + "\n"
        except Exception as exc:
            print(f"AI summary unavailable: {exc}", file=sys.stderr)
            report += "\n## Optional AI commentary\n\nUnavailable; the deterministic screening above remains valid.\n"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = now.strftime("%Y-%m-%d_%H%M")
    md_path = args.output_dir / f"research_{stem}.md"
    json_path = args.output_dir / f"research_{stem}.json"
    md_path.write_text(report, encoding="utf-8")
    json_path.write_text(json.dumps({"generated_at": now.isoformat(), "provider": "Yahoo Finance / yfinance", "symbols": symbols, "rows": rows, "errors": errors}, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Reports: {md_path} and {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
