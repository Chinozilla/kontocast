"""Parser für CAMT.053-Kontoauszüge (ISO-20022-XML).

Namespace-agnostisch (arbeitet auf local names), damit die Versionen
camt.053.001.02 bis .08 gleichermaßen gelesen werden. Beträge stehen
vorzeichenlos in <Amt>, die Richtung in <CdtDbtInd> (DBIT/CRDT).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from pathlib import Path

from kontocast.models import Transaction


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find(elem: ET.Element, *names: str) -> ET.Element | None:
    """Erstes Element entlang einer Kette von local names."""
    current = [elem]
    for name in names:
        current = [child for el in current for child in el if _local(child.tag) == name]
        if not current:
            return None
    return current[0]


def _first_text(elem: ET.Element | None, name: str) -> str:
    if elem is None:
        return ""
    for el in elem.iter():
        if _local(el.tag) == name and el.text:
            return el.text.strip()
    return ""


def parse(path: Path) -> list[Transaction]:
    root = ET.fromstring(path.read_bytes())
    iban = _first_text(root, "IBAN")
    txs: list[Transaction] = []
    for ntry in root.iter():
        if _local(ntry.tag) != "Ntry":
            continue
        amt_el = _find(ntry, "Amt")
        ind_el = _find(ntry, "CdtDbtInd")
        date_el = _find(ntry, "BookgDt", "Dt")
        if amt_el is None or ind_el is None or date_el is None:
            continue
        amount = Decimal(amt_el.text.strip())
        if (ind_el.text or "").strip() == "DBIT":
            amount = -amount
        tx_dtls = _find(ntry, "NtryDtls", "TxDtls")
        # Gegenpartei: bei Ausgang der Creditor, bei Eingang der Debtor
        party_name = "Cdtr" if amount < 0 else "Dbtr"
        party_el = _find(tx_dtls, "RltdPties", party_name) if tx_dtls is not None else None
        txs.append(
            Transaction(
                booking_date=date.fromisoformat(date_el.text.strip()),
                amount=amount,
                currency=amt_el.get("Ccy", "EUR"),
                counterparty=_first_text(party_el, "Nm"),
                purpose=_first_text(tx_dtls, "Ustrd"),
                account=iban,
                source_format="camt053",
            )
        )
    return txs
