"""Offline email tests; do not connect to Gmail."""
import json
import pytest
from stock_agent.email_report import prepare_email, send_latest

REPORT = {
    "generated_at": "2026-11-22T18:00:00+05:30",
    "rows": [
        {"symbol": "DEMO.NS", "rating": "Research candidate", "score": 81, "currency": "INR",
         "price": 100, "as_of": "2026-11-20", "risks": ["High P/E"]},
        {"symbol": "EXAMPLE.NS", "rating": "Low priority", "score": 21, "currency": "INR",
         "price": 120, "as_of": "2026-11-20", "risks": []},
    ],
}


def test_email_contains_evidence_and_attached_reports():
    msg = prepare_email(REPORT, "# Research", json.dumps(REPORT), "test@example.com", "https://github.com/example/repo")
    assert "1 research candidates" in msg["Subject"]
    assert msg["To"] == "test@example.com"
    assert "NOT a buy instruction" in msg.get_body(preferencelist=("plain",)).get_content()
    assert sorted(part.get_filename() for part in msg.iter_attachments()) == [
        "equity_research_2026-11-22.json", "equity_research_2026-11-22.md"
    ]


def test_missing_secrets_skips_delivery(tmp_path, monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    assert send_latest(tmp_path) is False


def test_gmail_delivery_uses_secrets_and_sends(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "test@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "demo secret")
    (tmp_path / "research_2026-11-22_1800.json").write_text(json.dumps(REPORT))
    (tmp_path / "research_2026-11-22_1800.md").write_text("# Research")
    seen = {}
    class FakeSMTP:
        def __init__(self, host, port, *, context, timeout):
            assert host == "smtp.gmail.com" and port == 465 and timeout == 30
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def login(self, username, password):
            seen["login"] = (username, password)
        def send_message(self, message):
            seen["message"] = message
    assert send_latest(tmp_path, smtp_factory=FakeSMTP) is True
    assert seen["login"] == ("test@example.com", "demosecret")
    assert seen["message"]["To"] == "test@example.com"


def test_empty_report_not_emailed(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "test@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "demo")
    (tmp_path / "research_2026-11-22_1800.json").write_text(json.dumps({"rows": []}))
    (tmp_path / "research_2026-11-22_1800.md").write_text("# No data")
    with pytest.raises(ValueError, match="No screened stocks"):
        send_latest(tmp_path)
