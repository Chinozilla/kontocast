"""Regel-Kategorisierung + Eval-Harness gegen die Synth-Ground-Truth."""

from datetime import date
from decimal import Decimal

from kontocast import synth
from kontocast.categorize import evaluate as ev
from kontocast.categorize import rules
from kontocast.models import Transaction


def _tx(counterparty: str, purpose: str) -> Transaction:
    return Transaction(
        booking_date=date(2026, 1, 2),
        amount=Decimal("-10.00"),
        currency="EUR",
        counterparty=counterparty,
        purpose=purpose,
        source_format="test",
    )


def test_basic_rules():
    assert rules.categorize(_tx("REWE Markt GmbH", "KARTENZAHLUNG")) == "Lebensmittel"
    assert rules.categorize(_tx("NETFLIX INTERNATIONAL B.V.", "ABO")) == "Abos & Medien"
    assert rules.categorize(_tx("Unbekannte Firma XY", "irgendwas")) == "Sonstiges"


def test_rules_accuracy_on_synthetic_ground_truth():
    ledger = synth.generate_ledger(months=12, seed=11)
    pairs = [(tx.with_category(None), tx.category) for tx in synth.to_transactions(ledger)]
    result = ev.evaluate(pairs, rules.categorize)
    assert result.accuracy >= 0.95


def test_labels_roundtrip(tmp_path):
    ledger = synth.write_all(tmp_path, months=4, seed=9)
    from kontocast.parsers import parse_file

    txs = parse_file(tmp_path / "dkb.csv")
    pairs = ev.load_labeled(tmp_path / "labels.csv", txs)
    assert len(pairs) == len(ledger)
