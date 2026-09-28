"""The load: write enriched rows into a SQLite warehouse table.

Replace semantics (delete-then-insert) make a re-run idempotent -- loading the
same batch twice leaves the table unchanged. The idempotency defect skips the
delete, so the load appends and a re-run doubles the rows. That is the classic
'the pipeline is not idempotent' bug, and the reconciliation check catches it.
"""

from __future__ import annotations

import sqlite3

COLUMNS = [
    "order_id", "customer_id", "customer_name", "country", "product_id",
    "product_name", "category", "quantity", "unit_price", "line_total",
    "order_date", "email",
]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS orders_enriched (
    {', '.join(c + ' ' + ('INTEGER' if c in ('order_id','customer_id','product_id','quantity') else 'REAL' if c in ('unit_price','line_total') else 'TEXT') for c in COLUMNS)}
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def load(conn: sqlite3.Connection, rows: list[dict], *, append: bool = False) -> None:
    if not append:
        conn.execute("DELETE FROM orders_enriched")     # replace => idempotent
    placeholders = ", ".join("?" for _ in COLUMNS)
    conn.executemany(
        f"INSERT INTO orders_enriched ({', '.join(COLUMNS)}) VALUES ({placeholders})",
        [tuple(r.get(c) for c in COLUMNS) for r in rows],
    )
    conn.commit()


def read(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM orders_enriched ORDER BY rowid")]
