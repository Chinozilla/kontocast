"""Monte-Carlo-Cashflow-Projektion.

Zweiteiliges Modell:
- Deterministischer Teil: erkannte wiederkehrende Posten (Gehalt, Miete, Abos)
  gehen mit ihrem auf den Monat normalisierten Betrag in jeden Zukunftsmonat ein.
- Stochastischer Teil: die variablen Monats-Summen (alles Nicht-Wiederkehrende)
  werden per Bootstrap aus der eigenen Historie gezogen (Resampling mit
  Zurücklegen) — keine Verteilungsannahme, die Schwankung kommt aus den Daten.

Ergebnis sind Perzentil-Korridore (p10/p50/p90) des Kontostands je Zukunftsmonat.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from kontocast.models import Transaction
from kontocast.recurring import RecurringItem, detect_recurring, normalize_name


@dataclass
class Forecast:
    months: list[str]  # "2026-07", ...
    p10: list[float]
    p50: list[float]
    p90: list[float]
    start_balance: float
    fixed_monthly: float  # Summe wiederkehrender Posten pro Monat
    n_sims: int


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def simulate(
    txs: list[Transaction],
    horizon_months: int = 12,
    n_sims: int = 1000,
    start_balance: float = 0.0,
    seed: int = 42,
    recurring: list[RecurringItem] | None = None,
) -> Forecast:
    if recurring is None:
        recurring = detect_recurring(txs)
    recurring_names = {normalize_name(r.counterparty) for r in recurring}
    fixed_monthly = float(sum(r.monthly_amount for r in recurring))

    # Historie der variablen Monats-Summen
    variable: dict[str, float] = {}
    for t in txs:
        if normalize_name(t.counterparty) in recurring_names:
            continue
        key = _month_key(t.booking_date)
        variable[key] = variable.get(key, 0.0) + float(t.amount)
    keys = sorted(variable)
    if len(keys) > 4:
        # Randmonate sind meist unvollständig exportiert — verzerren das Sampling
        keys = keys[1:-1]
    samples = np.array([variable[k] for k in keys]) if keys else np.array([0.0])

    rng = np.random.default_rng(seed)
    draws = rng.choice(samples, size=(n_sims, horizon_months), replace=True)
    paths = start_balance + np.cumsum(draws + fixed_monthly, axis=1)

    last = max(t.booking_date for t in txs) if txs else date.today()
    months: list[str] = []
    year, month = last.year, last.month
    for _ in range(horizon_months):
        month += 1
        if month > 12:
            month, year = 1, year + 1
        months.append(f"{year:04d}-{month:02d}")

    return Forecast(
        months=months,
        p10=np.percentile(paths, 10, axis=0).round(2).tolist(),
        p50=np.percentile(paths, 50, axis=0).round(2).tolist(),
        p90=np.percentile(paths, 90, axis=0).round(2).tolist(),
        start_balance=start_balance,
        fixed_monthly=round(fixed_monthly, 2),
        n_sims=n_sims,
    )
