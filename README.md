# Stock Research Agent

An evidence-based NSE equity screener for research, not trading. It uses a transparent rule-based ranking and optional AI-written commentary. No brokerage integration, trading orders, or guaranteed predictions.

Run `pip install -r requirements.txt`, then `python -m pytest -q` and `python -m stock_agent.cli --output-dir reports`.

Weekly GitHub Actions scans are configured for Mondays after the Indian cash market close. Get reports from **Actions → Weekly equity research → Artifacts**. Data comes from yfinance (unofficial, possibly stale/incomplete). AI commentary requires an `OPENAI_API_KEY` repository secret, and is disabled by default.

**Investment risk:** These are research leads, not personalized buy/sell recommendations. Review exchange filings, valuations and risks before taking a position.


## Automatic email delivery

The scan is scheduled on **Mondays at 17:45 Asia/Kolkata** (12:15 UTC). GitHub can delay scheduled jobs. Each successful scan can email a summary and attach Markdown + JSON reports.

To enable delivery, create **two GitHub Actions repository secrets** at **Settings → Secrets and variables → Actions → New repository secret**:

1. `GMAIL_ADDRESS`: the Gmail address that will send and receive these reports. No address is committed to this repository.
2. `GMAIL_APP_PASSWORD`: a Gmail **App Password**, **not** your normal Google password. Set up Google 2-Step Verification first, then create an App Password at https://myaccount.google.com/apppasswords if available.

The `GMAIL_ADDRESS` sender will email **itself**. The credentials are accessed only in the email step and are never written to source code or artifacts. Do not paste passwords into GitHub source code, workflow logs, issues, or ChatGPT. If either secret is absent, the email step logs a warning and skips mail; analysis reports are still available as workflow artifacts. If SMTP authentication fails, the email step fails with a logged error.

To test: **Actions → Weekly equity research → Run workflow**, with optional AI commentary turned off. Download artifacts after the job completes. You will receive an email only once the two secrets are configured, network delivery succeeds, and at least one stock has usable data.

The GitHub Actions workflow cannot authenticate to Gmail using your ChatGPT Gmail connector. App Password use can be revoked in Google Account security settings. Google Workspace or Advanced Protection accounts may not support App Passwords; use another secure email service in those cases.
