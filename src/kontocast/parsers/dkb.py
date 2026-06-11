"""Parser für den DKB-CSV-Export (Format ab 2023).

Kopfzeilen mit Kontostand, dann eine Tabelle mit Spalte "Betrag (€)".
Bei Eingängen steht die Gegenpartei in "Zahlungspflichtige*r",
bei Ausgängen in "Zahlungsempfänger*in".
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from kontocast.models import Transaction
from kontocast.parsers import parse_german_amount, parse_german_date, read_text_lenient


def parse(path: Path) -> list[Transaction]:
    text = read_text_lenient(path)
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if "Buchungsdatum" in line)
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])), delimiter=";")
    txs: list[Transaction] = []
    for row in reader:
        amount_raw = (row.get("Betrag (€)") or row.get("Betrag") or "").strip()
        if not amount_raw or not (row.get("Buchungsdatum") or "").strip():
            continue
        incoming = (row.get("Umsatztyp") or "").strip().lower() == "eingang"
        if incoming:
            counterparty = (row.get("Zahlungspflichtige*r") or "").strip()
        else:
            counterparty = (row.get("Zahlungsempfänger*in") or "").strip()
        txs.append(
            Transaction(
                booking_date=parse_german_date(row["Buchungsdatum"]),
                amount=parse_german_amount(amount_raw),
                currency="EUR",
                counterparty=counterparty,
                purpose=(row.get("Verwendungszweck") or "").strip(),
                account=(row.get("IBAN") or "").strip(),
                source_format="dkb",
            )
        )
    return txs
