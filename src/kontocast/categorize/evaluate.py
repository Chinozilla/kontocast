"""Eval-Harness: misst die Genauigkeit eines Kategorisierers gegen Ground-Truth-Labels.

Der synthetische Generator schreibt zu jeder Transaktion die wahre Kategorie
in labels.csv — damit ist die Kategorisierungs-Qualität (Regeln wie LLM)
messbar statt gefühlt.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from kontocast.models import Transaction


@dataclass
class EvalResult:
    total: int
    correct: int
    per_category: dict[str, tuple[int, int]]  # Kategorie -> (richtig, gesamt)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def load_labeled(labels_path: Path, txs: list[Transaction]) -> list[tuple[Transaction, str]]:
    """Joint Transaktionen mit Labels über (Datum, Betrag, Gegenpartei)."""
    labels: dict[tuple[str, str, str], str] = {}
    with open(labels_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            labels[(row["date"], row["amount"], row["counterparty"])] = row["category"]
    pairs: list[tuple[Transaction, str]] = []
    for t in txs:
        truth = labels.get((t.booking_date.isoformat(), str(t.amount), t.counterparty))
        if truth:
            pairs.append((t, truth))
    return pairs


def evaluate(
    pairs: list[tuple[Transaction, str]], categorizer: Callable[[Transaction], str]
) -> EvalResult:
    correct = 0
    per: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for tx, truth in pairs:
        prediction = categorizer(tx)
        per[truth][1] += 1
        if prediction == truth:
            correct += 1
            per[truth][0] += 1
    return EvalResult(
        total=len(pairs),
        correct=correct,
        per_category={k: (v[0], v[1]) for k, v in per.items()},
    )
