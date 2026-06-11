"""SQLite-Speicher — lokal, eine Datei, dedupliziert über tx_id."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

from kontocast.models import Transaction

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    tx_id TEXT PRIMARY KEY,
    booking_date TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    counterparty TEXT NOT NULL,
    purpose TEXT NOT NULL,
    account TEXT NOT NULL DEFAULT '',
    source_format TEXT NOT NULL,
    category TEXT
)
"""


def connect(db_path: Path | str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute(SCHEMA)
    return con


def add_transactions(con: sqlite3.Connection, txs: list[Transaction]) -> int:
    """Fügt Transaktionen ein; bereits bekannte (gleiche tx_id) werden übersprungen."""
    cur = con.executemany(
        "INSERT OR IGNORE INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (
                t.tx_id,
                t.booking_date.isoformat(),
                str(t.amount),
                t.currency,
                t.counterparty,
                t.purpose,
                t.account,
                t.source_format,
                t.category,
            )
            for t in txs
        ],
    )
    con.commit()
    return cur.rowcount


def load_transactions(con: sqlite3.Connection) -> list[Transaction]:
    rows = con.execute(
        "SELECT booking_date, amount, currency, counterparty, purpose,"
        " source_format, account, category"
        " FROM transactions ORDER BY booking_date"
    ).fetchall()
    return [
        Transaction(
            booking_date=date.fromisoformat(r[0]),
            amount=Decimal(r[1]),
            currency=r[2],
            counterparty=r[3],
            purpose=r[4],
            source_format=r[5],
            account=r[6],
            category=r[7],
        )
        for r in rows
    ]


def set_categories(con: sqlite3.Connection, mapping: dict[str, str]) -> None:
    """mapping: tx_id -> Kategorie."""
    con.executemany(
        "UPDATE transactions SET category = ? WHERE tx_id = ?",
        [(category, tx_id) for tx_id, category in mapping.items()],
    )
    con.commit()
