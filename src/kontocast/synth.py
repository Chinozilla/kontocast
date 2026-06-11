"""Synthetische Kontoauszüge: ein realistischer Haushalt über N Monate.

Erzeugt dieselbe Buchungs-Historie in vier echten deutschen Bank-Export-
Formaten (DKB-CSV, ING-CSV, Sparkasse-CSV-CAMT, CAMT.053-XML) plus eine
Ground-Truth-Label-Datei für den Eval-Harness. Deterministisch über seed —
dient zugleich als Demo-Datensatz und als Test-Fixture.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

from kontocast.models import Transaction

HOLDER = "Max Mustermann"
IBAN = "DE02120300000000202051"
CAMT_NS = "urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"


@dataclass(frozen=True)
class SynthTx:
    booking_date: date
    amount: Decimal
    counterparty: str
    purpose: str
    category: str


def _d(value: float) -> Decimal:
    return Decimal(f"{value:.2f}")


def _german(amount: Decimal) -> str:
    return f"{amount:.2f}".replace(".", ",")


def generate_ledger(months: int = 18, seed: int = 42, end: date | None = None) -> list[SynthTx]:
    rng = random.Random(seed)
    end = end or date.today()
    start = end.replace(day=1)
    for _ in range(months - 1):
        start = (start - timedelta(days=1)).replace(day=1)

    grocers = ["REWE Markt GmbH", "EDEKA Center", "LIDL Dienstleistung", "ALDI SUED"]
    restaurants = ["Lieferando.de", "Pizzeria Bella Italia", "Cafe Central", "McDonalds Deutschland"]
    shops = ["AMAZON EU S.A R.L.", "Zalando SE", "MediaMarkt"]

    txs: list[SynthTx] = []
    ref = 0

    def add(d: date, amount: Decimal, counterparty: str, purpose: str, category: str) -> None:
        nonlocal ref
        ref += 1
        txs.append(SynthTx(d, amount, counterparty, f"{purpose} REF{ref:05d}", category))

    cur = start
    while cur <= end:
        y, m = cur.year, cur.month
        stamp = f"{m:02d}/{y}"

        def dom(day: int) -> date:
            return date(y, m, min(day, 28))

        # Fixposten
        add(dom(28), _d(2850.00), "Acme Software GmbH", f"GEHALT {stamp}", "Einkommen")
        add(dom(1), _d(-980.00), "Wohnbau Hanau GmbH", f"MIETE BERGSTRASSE 3 {stamp}", "Wohnen")
        add(dom(3), _d(-128.00), "Stadtwerke Hanau", f"ABSCHLAG STROM GAS {stamp}", "Nebenkosten & Energie")
        add(dom(15), _d(-13.99), "NETFLIX INTERNATIONAL B.V.", f"NETFLIX ABO {stamp}", "Abos & Medien")
        add(dom(7), _d(-10.99), "Spotify AB", f"SPOTIFY PREMIUM {stamp}", "Abos & Medien")
        add(dom(20), _d(-29.90), "FitX Deutschland GmbH", f"MITGLIEDSBEITRAG FITNESS {stamp}", "Freizeit & Gastro")
        add(dom(25), _d(-200.00), "Trade Republic Bank GmbH", f"SPARPLAN ETF MSCI WORLD {stamp}", "Sparen & Anlegen")
        add(dom(18), _d(-19.99), "Telekom Deutschland GmbH", f"MOBILFUNK RECHNUNG {stamp}", "Abos & Medien")
        add(dom(27), _d(-4.90), "Sparkasse Hanau", f"ENTGELT KONTOFUEHRUNG {stamp}", "Bank & Gebühren")

        # Variable Posten
        for _ in range(rng.randint(8, 12)):
            add(date(y, m, rng.randint(1, 28)), _d(-rng.uniform(8, 95)),
                rng.choice(grocers), "KARTENZAHLUNG DANKE", "Lebensmittel")
        for _ in range(rng.randint(2, 5)):
            add(date(y, m, rng.randint(1, 28)), _d(-rng.uniform(9, 60)),
                rng.choice(restaurants), "BESTELLUNG DANKE", "Freizeit & Gastro")
        for _ in range(rng.randint(0, 3)):
            add(date(y, m, rng.randint(1, 28)), _d(-rng.uniform(10, 140)),
                rng.choice(shops), "ONLINE EINKAUF", "Shopping")
        if rng.random() < 0.7:
            add(date(y, m, rng.randint(1, 28)), _d(-rng.choice([50.0, 100.0, 150.0])),
                "Geldautomat Sparkasse", "BARGELDAUSZAHLUNG", "Bargeld")
        if rng.random() < 0.5:
            add(date(y, m, rng.randint(1, 28)), _d(-rng.uniform(15, 80)),
                "DB Vertrieb GmbH", "FAHRKARTE DEUTSCHE BAHN", "Mobilität")
        if rng.random() < 0.4:
            add(date(y, m, rng.randint(1, 28)), _d(-rng.uniform(5, 45)),
                "dm-drogerie markt", "EINKAUF DROGERIE", "Gesundheit")

        # Jahresposten
        if m == 4:
            add(dom(10), _d(-89.00), "HUK-COBURG Versicherung", f"HAFTPFLICHT JAHRESBEITRAG {y}", "Versicherung")

        cur = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)

    result = [t for t in txs if t.booking_date <= end]
    result.sort(key=lambda t: (t.booking_date, t.purpose))
    return result


def to_transactions(ledger: list[SynthTx]) -> list[Transaction]:
    return [
        Transaction(
            booking_date=t.booking_date,
            amount=t.amount,
            currency="EUR",
            counterparty=t.counterparty,
            purpose=t.purpose,
            source_format="synth",
            category=t.category,
        )
        for t in ledger
    ]


def write_dkb(ledger: list[SynthTx], path: Path) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(["Girokonto", IBAN])
        w.writerow([])
        w.writerow([
            "Buchungsdatum", "Wertstellung", "Status", "Zahlungspflichtige*r",
            "Zahlungsempfänger*in", "Verwendungszweck", "Umsatztyp", "IBAN",
            "Betrag (€)", "Gläubiger-ID", "Mandatsreferenz", "Kundenreferenz",
        ])
        for t in ledger:
            incoming = t.amount > 0
            w.writerow([
                t.booking_date.strftime("%d.%m.%y"),
                t.booking_date.strftime("%d.%m.%y"),
                "Gebucht",
                t.counterparty if incoming else HOLDER,
                HOLDER if incoming else t.counterparty,
                t.purpose,
                "Eingang" if incoming else "Ausgang",
                IBAN,
                _german(t.amount),
                "", "", "",
            ])


def write_ing(ledger: list[SynthTx], path: Path) -> None:
    with open(path, "w", encoding="cp1252", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Umsatzanzeige", "Girokonto"])
        w.writerow([])
        w.writerow(["IBAN", IBAN])
        w.writerow(["Kontoname", "Girokonto"])
        w.writerow(["Bank", "ING"])
        w.writerow(["Kunde", HOLDER])
        w.writerow([])
        w.writerow([
            "Buchung", "Valuta", "Auftraggeber/Empfänger", "Buchungstext",
            "Verwendungszweck", "Saldo", "Währung", "Betrag", "Währung",
        ])
        for t in ledger:
            w.writerow([
                t.booking_date.strftime("%d.%m.%Y"),
                t.booking_date.strftime("%d.%m.%Y"),
                t.counterparty,
                "Gutschrift" if t.amount > 0 else "Lastschrift",
                t.purpose,
                "", "EUR",
                _german(t.amount),
                "EUR",
            ])


SPARKASSE_COLUMNS = [
    "Auftragskonto", "Buchungstag", "Valutadatum", "Buchungstext", "Verwendungszweck",
    "Glaeubiger ID", "Mandatsreferenz", "Kundenreferenz (End-to-End)", "Sammlerreferenz",
    "Lastschrift Ursprungsbetrag", "Auslagenersatz Ruecklastschrift",
    "Beguenstigter/Zahlungspflichtiger", "Kontonummer/IBAN", "BIC (SWIFT-Code)",
    "Betrag", "Waehrung", "Info",
]


def write_sparkasse(ledger: list[SynthTx], path: Path) -> None:
    with open(path, "w", encoding="cp1252", newline="") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow(SPARKASSE_COLUMNS)
        for t in ledger:
            w.writerow([
                IBAN,
                t.booking_date.strftime("%d.%m.%y"),
                t.booking_date.strftime("%d.%m.%y"),
                "GUTSCHR. UEBERWEISUNG" if t.amount > 0 else "FOLGELASTSCHRIFT",
                t.purpose,
                "", "", "", "", "", "",
                t.counterparty,
                IBAN,
                "HELADEF1HAN",
                _german(t.amount),
                "EUR",
                "Umsatz gebucht",
            ])


def write_camt053(ledger: list[SynthTx], path: Path) -> None:
    entries = []
    for t in ledger:
        indicator = "CRDT" if t.amount > 0 else "DBIT"
        party_tag = "Dbtr" if indicator == "CRDT" else "Cdtr"
        entries.append(f"""
      <Ntry>
        <Amt Ccy="EUR">{abs(t.amount)}</Amt>
        <CdtDbtInd>{indicator}</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>{t.booking_date.isoformat()}</Dt></BookgDt>
        <NtryDtls><TxDtls>
          <RltdPties><{party_tag}><Pty><Nm>{escape(t.counterparty)}</Nm></Pty></{party_tag}></RltdPties>
          <RmtInf><Ustrd>{escape(t.purpose)}</Ustrd></RmtInf>
        </TxDtls></NtryDtls>
      </Ntry>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="{CAMT_NS}">
  <BkToCstmrStmt>
    <Stmt>
      <Id>KONTOCAST-SYNTH</Id>
      <Acct><Id><IBAN>{IBAN}</IBAN></Id></Acct>{"".join(entries)}
    </Stmt>
  </BkToCstmrStmt>
</Document>
"""
    path.write_text(xml, encoding="utf-8")


def write_labels(ledger: list[SynthTx], path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["date", "amount", "counterparty", "category"])
        for t in ledger:
            w.writerow([t.booking_date.isoformat(), str(t.amount), t.counterparty, t.category])


def write_all(outdir: Path, months: int = 18, seed: int = 42) -> list[SynthTx]:
    outdir.mkdir(parents=True, exist_ok=True)
    ledger = generate_ledger(months=months, seed=seed)
    write_dkb(ledger, outdir / "dkb.csv")
    write_ing(ledger, outdir / "ing.csv")
    write_sparkasse(ledger, outdir / "sparkasse.csv")
    write_camt053(ledger, outdir / "camt053.xml")
    write_labels(ledger, outdir / "labels.csv")
    return ledger
