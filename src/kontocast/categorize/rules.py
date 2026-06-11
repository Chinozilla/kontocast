"""Regelbasierte Kategorisierung — deterministische, offline Baseline.

Die Regeln matchen als Substring auf Gegenpartei + Verwendungszweck
(lowercased); die erste passende Regel gewinnt, daher stehen spezifische
Begriffe vor generischen.
"""

from __future__ import annotations

from kontocast.models import Transaction

CATEGORIES = [
    "Einkommen",
    "Wohnen",
    "Nebenkosten & Energie",
    "Lebensmittel",
    "Abos & Medien",
    "Versicherung",
    "Mobilität",
    "Gesundheit",
    "Freizeit & Gastro",
    "Shopping",
    "Bargeld",
    "Bank & Gebühren",
    "Sparen & Anlegen",
    "Sonstiges",
]

RULES: list[tuple[str, str]] = [
    # Einkommen
    ("gehalt", "Einkommen"),
    ("lohn", "Einkommen"),
    ("bezuege", "Einkommen"),
    # Wohnen
    ("miete", "Wohnen"),
    ("hausverwaltung", "Wohnen"),
    ("wohnbau", "Wohnen"),
    ("wohnungsgenossenschaft", "Wohnen"),
    # Nebenkosten & Energie
    ("stadtwerke", "Nebenkosten & Energie"),
    ("strom", "Nebenkosten & Energie"),
    ("vattenfall", "Nebenkosten & Energie"),
    ("e.on", "Nebenkosten & Energie"),
    ("gasag", "Nebenkosten & Energie"),
    # Sparen & Anlegen (vor Bank-Gebühren, "sparplan" vor "spar...")
    ("trade republic", "Sparen & Anlegen"),
    ("scalable capital", "Sparen & Anlegen"),
    ("sparplan", "Sparen & Anlegen"),
    ("depot", "Sparen & Anlegen"),
    # Bargeld (vor Bank & Gebühren)
    ("geldautomat", "Bargeld"),
    ("bargeldauszahlung", "Bargeld"),
    ("atm", "Bargeld"),
    # Bank & Gebühren
    ("entgelt", "Bank & Gebühren"),
    ("kontofuehrung", "Bank & Gebühren"),
    ("kontoführung", "Bank & Gebühren"),
    ("gebuehr", "Bank & Gebühren"),
    ("dispozins", "Bank & Gebühren"),
    # Lebensmittel
    ("rewe", "Lebensmittel"),
    ("edeka", "Lebensmittel"),
    ("lidl", "Lebensmittel"),
    ("aldi", "Lebensmittel"),
    ("netto marken", "Lebensmittel"),
    ("penny", "Lebensmittel"),
    ("kaufland", "Lebensmittel"),
    # Abos & Medien
    ("netflix", "Abos & Medien"),
    ("spotify", "Abos & Medien"),
    ("disney", "Abos & Medien"),
    ("amazon prime", "Abos & Medien"),
    ("youtube premium", "Abos & Medien"),
    ("rundfunk", "Abos & Medien"),
    ("telekom", "Abos & Medien"),
    ("vodafone", "Abos & Medien"),
    ("o2 ", "Abos & Medien"),
    ("mobilfunk", "Abos & Medien"),
    # Versicherung
    ("versicherung", "Versicherung"),
    ("haftpflicht", "Versicherung"),
    ("allianz", "Versicherung"),
    ("huk", "Versicherung"),
    ("axa", "Versicherung"),
    # Mobilität
    ("db vertrieb", "Mobilität"),
    ("deutsche bahn", "Mobilität"),
    ("bahn", "Mobilität"),
    ("shell", "Mobilität"),
    ("aral", "Mobilität"),
    ("tankstelle", "Mobilität"),
    ("hvv", "Mobilität"),
    ("rmv", "Mobilität"),
    ("mvg", "Mobilität"),
    ("bvg", "Mobilität"),
    ("flixbus", "Mobilität"),
    # Gesundheit
    ("apotheke", "Gesundheit"),
    ("drogerie", "Gesundheit"),
    ("rossmann", "Gesundheit"),
    ("zahnarzt", "Gesundheit"),
    # Freizeit & Gastro
    ("lieferando", "Freizeit & Gastro"),
    ("pizz", "Freizeit & Gastro"),  # matcht "pizza" UND "pizzeria"
    ("restaurant", "Freizeit & Gastro"),
    ("cafe", "Freizeit & Gastro"),
    ("mcdonald", "Freizeit & Gastro"),
    ("burger", "Freizeit & Gastro"),
    ("kino", "Freizeit & Gastro"),
    ("fitness", "Freizeit & Gastro"),
    ("fitx", "Freizeit & Gastro"),
    ("mcfit", "Freizeit & Gastro"),
    # Shopping
    ("amazon", "Shopping"),
    ("zalando", "Shopping"),
    ("otto", "Shopping"),
    ("mediamarkt", "Shopping"),
    ("media markt", "Shopping"),
    ("saturn", "Shopping"),
    ("h&m", "Shopping"),
    ("ikea", "Shopping"),
]


def categorize(tx: Transaction) -> str:
    text = f"{tx.counterparty} {tx.purpose}".lower()
    for needle, category in RULES:
        if needle in text:
            return category
    return "Sonstiges"
