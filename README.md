# Stock Research Agent

An evidence-based NSE equity screener for research, not trading. It uses a transparent rule-based ranking and optional AI-written commentary. No brokerage integration, trading orders, or guaranteed predictions.

Run `pip install -r requirements.txt`, then `python -m pytest -q` and `python -m stock_agent.cli --output-dir reports`.

Weekly GitHub Actions scans are configured for Mondays after the Indian cash market close. Get reports from **Actions → Weekly equity research → Artifacts**. Data comes from yfinance (unofficial, possibly stale/incomplete). AI commentary requires an `OPENAI_API_KEY` repository secret, and is disabled by default.

**Investment risk:** These are research leads, not personalized buy/sell recommendations. Review exchange filings, valuations and risks before taking a position.
