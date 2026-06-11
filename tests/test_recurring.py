"""Recurring-Erkennung: gepflanzte Fixposten müssen gefunden werden, Variables nicht."""

from decimal import Decimal

from kontocast import synth
from kontocast.recurring import detect_recurring


def test_detects_planted_fixed_items():
    txs = synth.to_transactions(synth.generate_ledger(months=12, seed=3))
    items = detect_recurring(txs)
    by_name = {i.counterparty: i for i in items}

    rent = by_name["Wohnbau Hanau GmbH"]
    assert rent.period_label == "monatlich"
    assert rent.median_amount == Decimal("-980.00")

    salary = by_name["Acme Software GmbH"]
    assert salary.period_label == "monatlich"
    assert salary.median_amount == Decimal("2850.00")

    assert "NETFLIX INTERNATIONAL B.V." in by_name
    assert "Spotify AB" in by_name


def test_variable_spending_is_not_recurring():
    txs = synth.to_transactions(synth.generate_ledger(months=12, seed=3))
    names = {i.counterparty for i in detect_recurring(txs)}
    # Supermärkte kaufen wir oft, aber unregelmäßig — kein Abo
    assert not any("REWE" in n or "EDEKA" in n or "LIDL" in n or "ALDI" in n for n in names)
