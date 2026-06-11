"""Format-Erkennung und Dispatch auf die Bank-Parser.

Deutsche Banken liefern semikolon-getrennte CSVs mit deutschem Zahlenformat
(Komma als Dezimaltrenner) in wechselnden Encodings, oder CAMT.053-XML.
Jeder Parser normalisiert in das gemeinsame Transaction-Modell.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from kontocast.models import Transaction

ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def read_text_lenient(path: Path) -> str:
    data = path.read_bytes()
    for enc in ENCODINGS:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def parse_german_amount(raw: str) -> Decimal:
    s = raw.strip().replace("\xa0", "").replace(" ", "").replace("EUR", "").replace("€", "")
    s = s.replace(".", "").replace(",", ".")
    if not s or s in {"-", "+"}:
        raise ValueError(f"Kein Betrag: {raw!r}")
    return Decimal(s)


def parse_german_date(raw: str) -> date:
    s = raw.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Kein Datum: {raw!r}")


def detect_format(path: Path) -> str:
    head = read_text_lenient(path)[:4000].lower()
    if head.lstrip().startswith("<?xml") or "camt.053" in head:
        return "camt053"
    if "auftragskonto" in head and "beguenstigter" in head:
        return "sparkasse"
    if "umsatzanzeige" in head or "auftraggeber/empfänger" in head:
        return "ing"
    if "buchungsdatum" in head and ("umsatztyp" in head or "betrag (€)" in head):
        return "dkb"
    raise ValueError(f"Unbekanntes Format: {path.name}")


def parse_file(path: Path) -> list[Transaction]:
    fmt = detect_format(path)
    from kontocast.parsers import camt053, dkb, ing, sparkasse

    module = {"camt053": camt053, "dkb": dkb, "ing": ing, "sparkasse": sparkasse}[fmt]
    return module.parse(path)
