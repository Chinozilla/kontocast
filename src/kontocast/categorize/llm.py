"""LLM-Kategorisierung (optional) über die Anthropic-API.

Wird nur genutzt, wenn das Extra `kontocast[llm]` installiert und
ANTHROPIC_API_KEY gesetzt ist. Der Kern des Tools bleibt komplett offline.
"""

from __future__ import annotations

import json
import os

from kontocast.categorize.rules import CATEGORIES
from kontocast.models import Transaction

MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 50

PROMPT = """Du bist ein Buchhaltungs-Assistent. Ordne jede Banktransaktion GENAU einer Kategorie zu.
Erlaubte Kategorien: {cats}

Transaktionen (id | betrag | gegenpartei | verwendungszweck):
{lines}

Antworte NUR mit einem JSON-Objekt der Form {{"<id>": "<Kategorie>", ...}} ohne weiteren Text."""


def categorize_batch(txs: list[Transaction]) -> dict[str, str]:
    """Gibt tx_id -> Kategorie zurück; unbekannte Antworten fallen auf 'Sonstiges'."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("LLM-Extra fehlt: pip install kontocast[llm]") from exc
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY ist nicht gesetzt.")

    client = anthropic.Anthropic()
    result: dict[str, str] = {}
    for i in range(0, len(txs), BATCH_SIZE):
        chunk = txs[i : i + BATCH_SIZE]
        lines = "\n".join(
            f"{t.tx_id} | {t.amount} | {t.counterparty} | {t.purpose}" for t in chunk
        )
        message = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(cats=", ".join(CATEGORIES), lines=lines),
                }
            ],
        )
        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        data = json.loads(text)
        for t in chunk:
            category = data.get(t.tx_id)
            result[t.tx_id] = category if category in CATEGORIES else "Sonstiges"
    return result
