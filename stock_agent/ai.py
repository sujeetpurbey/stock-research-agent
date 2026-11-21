"""Optional constrained LLM narrative; not allowed to change rankings or introduce facts."""
from __future__ import annotations

import json
import os
from typing import Any


def generate_narrative(rows: list[dict[str, Any]], model: str | None = None) -> str:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY required only when --ai-summary is requested")
    from openai import OpenAI

    candidates = [r for r in rows if r["rating"] in ("Research candidate", "Watchlist")]
    evidence = [
        {k: r[k] for k in ("symbol", "name", "sector", "as_of", "rating", "score", "components", "evidence", "risks", "confidence")}
        for r in candidates[:10]
    ]
    if not evidence:
        return "No candidates passed the data requirements; an AI narrative was not generated."
    response = OpenAI().responses.create(
        model=model or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You are an evidence-constrained equity research note writer. Use ONLY supplied JSON. "
            "Summarize why these stocks are research candidates and state risks and missing evidence. "
            "Never introduce news, earnings, future facts, live quotes, fair values, target prices, "
            "expected returns, recommended allocations, or specific buy/sell commands. "
            "Do not change rank, score, classification or any number. "
            "Say scores are heuristic and not validated predictions. Maximum 350 words."
        ),
        input=json.dumps(evidence, allow_nan=False),
        max_output_tokens=550,
    )
    return response.output_text.strip()
