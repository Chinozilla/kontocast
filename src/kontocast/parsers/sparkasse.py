"""Parser für den Sparkassen-Export im "CSV-CAMT"-Format.

Eine flache, voll gequotete Semikolon-Tabelle; Gegenpartei steht in
"Beguenstigter/Zahlungspflichtiger" (für beide Richtungen dieselbe Spalte).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from kontocast.models import Transaction
from kontocast.parsers import parse_german_amount, parse_german_date, read_text_lenient


def parse(path: Path) -> list[Transaction]:
    text = read_text_lenient(path)
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    txs: list[Transaction] = []
    for row in reader:
        amount_raw = (row.get("Betrag") or "").strip()
        if not amount_raw or not (row.get("Buchungstag") or "").strip():
            continue
        txs.append(
            Transaction(
                booking_date=parse_german_date(row["Buchungstag"]),
                amount=parse_german_amount(amount_raw),
                currency=(row.get("Waehrung") or "EUR").strip() or "EUR",
                counterparty=(row.get("Beguenstigter/Zahlungspflichtiger") or "").strip(),
                purpose=(row.get("Verwendungszweck") or "").strip(),
                account=(row.get("Auftragskonto") or "").strip(),
                source_format="sparkasse",
            )
        )
    return txs
