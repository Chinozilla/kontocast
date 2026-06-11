"""Parser für den ING-CSV-Export ("Umsatzanzeige").

Metadaten-Block (IBAN, Kunde, Zeitraum), dann die Tabelle ab "Buchung;...".
Die Kopfzeile enthält "Währung" doppelt, daher Index-basierter Zugriff
statt DictReader.
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
    start = next(i for i, line in enumerate(lines) if line.startswith("Buchung;"))
    rows = list(csv.reader(io.StringIO("\n".join(lines[start:])), delimiter=";"))
    header = rows[0]
    idx = {name: i for i, name in enumerate(header)}  # bei Dubletten gewinnt die letzte
    i_betrag = header.index("Betrag")
    txs: list[Transaction] = []
    for row in rows[1:]:
        if len(row) < len(header) or not row[i_betrag].strip():
            continue
        txs.append(
            Transaction(
                booking_date=parse_german_date(row[idx["Buchung"]]),
                amount=parse_german_amount(row[i_betrag]),
                currency="EUR",
                counterparty=row[idx["Auftraggeber/Empfänger"]].strip(),
                purpose=row[idx["Verwendungszweck"]].strip(),
                source_format="ing",
            )
        )
    return txs
