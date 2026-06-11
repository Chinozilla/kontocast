"""Erkennung wiederkehrender Zahlungen (Miete, Abos, Gehalt) aus Intervall-Mustern.

Gruppiert nach Gegenpartei + Vorzeichen, prüft die Abstände zwischen den
Buchungstagen gegen bekannte Perioden (wöchentlich bis jährlich) und
verlangt stabile Beträge — variable Ausgaben wie Supermarkt-Einkäufe
fallen damit heraus.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median

from kontocast.models import Transaction

# (Periodenlänge in Tagen, Untergrenze, Obergrenze, Label)
PERIODS = [
    (7, 5, 9, "wöchentlich"),
    (30, 26, 35, "monatlich"),
    (91, 80, 100, "vierteljährlich"),
    (365, 330, 400, "jährlich"),
]

MAX_AMOUNT_SPREAD = Decimal("0.35")  # Median-Abweichung relativ zum Median-Betrag


@dataclass(frozen=True)
class RecurringItem:
    counterparty: str
    period_days: int
    period_label: str
    median_amount: Decimal
    occurrences: int
    first_date: date
    last_date: date

    @property
    def monthly_amount(self) -> Decimal:
        """Auf einen Monat normalisierter Betrag (30,44 Tage = mittlerer Monat)."""
        return (self.median_amount * Decimal("30.44") / Decimal(self.period_days)).quantize(
            Decimal("0.01")
        )


def normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def detect_recurring(txs: list[Transaction], min_occurrences: int = 3) -> list[RecurringItem]:
    groups: dict[tuple[str, bool], list[Transaction]] = {}
    for t in txs:
        key = (normalize_name(t.counterparty), t.amount > 0)
        groups.setdefault(key, []).append(t)

    items: list[RecurringItem] = []
    for (name, _positive), group in groups.items():
        if not name or len(group) < min_occurrences:
            continue
        group.sort(key=lambda t: t.booking_date)
        dates = sorted({t.booking_date for t in group})
        if len(dates) < min_occurrences:
            continue
        gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
        median_gap = median(gaps)
        for period_days, lo, hi, label in PERIODS:
            if not (lo <= median_gap <= hi):
                continue
            # Mindestens 60 % der Abstände müssen ins Periodenfenster fallen.
            if sum(1 for g in gaps if lo <= g <= hi) < len(gaps) * 0.6:
                break
            amounts = [t.amount for t in group]
            median_amount = Decimal(median(amounts))
            if median_amount == 0:
                break
            spread = median([abs(a - median_amount) for a in amounts])
            if spread / abs(median_amount) > MAX_AMOUNT_SPREAD:
                break
            items.append(
                RecurringItem(
                    counterparty=group[0].counterparty,
                    period_days=period_days,
                    period_label=label,
                    median_amount=median_amount.quantize(Decimal("0.01")),
                    occurrences=len(group),
                    first_date=dates[0],
                    last_date=dates[-1],
                )
            )
            break
    return sorted(items, key=lambda i: i.monthly_amount)
