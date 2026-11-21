"""Email the latest stock research report using GitHub Actions secrets and Gmail SMTP."""
from __future__ import annotations

import argparse
from email.message import EmailMessage
from html import escape
import json
import os
from pathlib import Path
import smtplib
import ssl
import sys


def prepare_email(report: dict, markdown: str, json_text: str, sender: str, repo_url: str) -> EmailMessage:
    """Create a concise digest with the full, reproducible evidence attached."""
    date = str(report.get("generated_at", "unknown date"))[:10]
    rows = report.get("rows") or []
    eligible = [r for r in rows if r.get("rating") in ("Research candidate", "Watchlist")]
    eligible.sort(key=lambda r: (r.get("rating") != "Research candidate", -r.get("score", 0)))
    top = eligible[:8]
    count = sum(r.get("rating") == "Research candidate" for r in eligible)

    lines = [
        f"Stock Research Agent — {date}",
        "",
        f"Screened {len(rows)} stocks; {count} passed the research-candidate threshold.",
        "This is a heuristic screen, NOT a buy instruction, forecast, or personalized investment advice.",
        "",
    ]
    if not top:
        lines.append("No research candidates or watchlist names passed the checks.")
    for r in top:
        lines.extend([
            f"{r.get('symbol', 'Unknown')} — {r.get('rating', 'Unknown')} ({r.get('score', '?')}/100)",
            f"  Last close: {r.get('currency', '')} {r.get('price', 'N/A')} | Data date: {r.get('as_of', 'N/A')}",
            f"  Screened risks: {', '.join(r.get('risks', [])) or 'No preset flags; other risks may exist.'}",
        ])
    lines += [
        "", "Markdown and JSON evidence reports are attached.",
        f"Agent repository: {repo_url}",
        "Source: Yahoo Finance/yfinance (unofficial; delays and missing/inaccurate data possible).",
        "Verify official company filings and portfolio suitability before acting.",
    ]

    table_rows = "".join(
        "<tr>"
        f"<td style='padding:8px;border-bottom:1px solid #ddd'>{escape(str(r.get('symbol', '')))}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #ddd'>{escape(str(r.get('rating', '')))}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #ddd;text-align:right'>{escape(str(r.get('score', '')))}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #ddd'>{escape(str(r.get('as_of', '')))}</td>"
        "</tr>"
        for r in top
    )
    html = (
        "<div style='font-family:Arial,sans-serif;max-width:700px;color:#1f2937'>"
        f"<h2>Indian Equity Research — {escape(date)}</h2>"
        f"<p>Screened <b>{len(rows)}</b> stocks; <b>{count}</b> research candidates.</p>"
        "<p><b>Research only:</b> heuristic scores are not return forecasts or buy recommendations.</p>"
        "<table style='border-collapse:collapse;width:100%'>"
        "<thead><tr style='background:#f3f4f6'><th style='text-align:left'>Ticker</th>"
        "<th style='text-align:left'>Screen</th><th>Score</th><th>Data date</th></tr></thead>"
        f"<tbody>{table_rows or '<tr><td colspan=4>No candidates passed.</td></tr>'}</tbody></table>"
        "<p>See the attached Markdown and JSON reports for evidence and risk warnings.</p>"
        f"<p><a href='{escape(repo_url, quote=True)}'>Open your stock research agent</a></p>"
        "<p style='font-size:12px;color:#6b7280'>Yahoo Finance data may be delayed, incomplete or wrong. "
        "Always verify source filings. No orders were placed.</p></div>"
    )

    message = EmailMessage()
    message["Subject"] = f"India Equity Research | {date} | {count} research candidates"
    message["From"] = sender
    message["To"] = sender
    message.set_content("\n".join(lines))
    message.add_alternative(html, subtype="html")
    message.add_attachment(markdown.encode("utf-8"), maintype="text", subtype="markdown",
                           filename=f"equity_research_{date}.md")
    message.add_attachment(json_text.encode("utf-8"), maintype="application", subtype="json",
                           filename=f"equity_research_{date}.json")
    return message


def send_latest(output_dir: Path, *, smtp_factory=smtplib.SMTP_SSL) -> bool:
    """Return False for unconfigured delivery; raise errors for failed attempted delivery."""
    sender = os.environ.get("GMAIL_ADDRESS", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not sender or not password:
        print("::warning::Email NOT sent: configure GMAIL_ADDRESS and GMAIL_APP_PASSWORD as GitHub Actions secrets.")
        return False
    if "\r" in sender or "\n" in sender or "@" not in sender:
        raise ValueError("GMAIL_ADDRESS must contain exactly one valid email address")

    reports = sorted(output_dir.glob("research_*.json"))
    if not reports:
        raise FileNotFoundError(f"No JSON report found in {output_dir}")
    json_path = reports[-1]
    md_path = json_path.with_suffix(".md")
    if not md_path.is_file():
        raise FileNotFoundError(f"Markdown report missing: {md_path}")
    json_text = json_path.read_text(encoding="utf-8")
    report = json.loads(json_text)
    if not report.get("rows"):
        raise ValueError("No screened stocks; email not sent")

    message = prepare_email(
        report, md_path.read_text(encoding="utf-8"), json_text,
        sender, "https://github.com/sujeetpurbey/stock-research-agent",
    )
    with smtp_factory("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)
    print("Success: email report sent to configured Gmail inbox.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Email the latest stock research report")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()
    try:
        send_latest(args.output_dir)
        return 0
    except Exception as exc:
        print(f"ERROR: email delivery failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
