"""Kerndatenmodell: eine Banktransaktion, format-unabhängig."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Transaction:
    booking_date: date
    amount: Decimal  # negativ = Ausgabe, positiv = Einnahme
    currency: str
    counterparty: str
    purpose: str
    source_format: str
    account: str = ""
    category: str | None = None

    @property
    def tx_id(self) -> str:
        # Identisch über alle Bank-Formate hinweg, damit derselbe Umsatz aus
        # verschiedenen Export-Dateien beim Import dedupliziert wird.
        raw = "|".join(
            [self.booking_date.isoformat(), str(self.amount), self.counterparty, self.purpose]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def with_category(self, category: str | None) -> "Transaction":
        return replace(self, category=category)
