"""The transform: pure helper functions plus the join/derive step.

The helpers are side-effect-free and property-tested. The transform itself is
deliberately *mechanical* -- it joins, casts and derives, but it does NOT validate
or silently repair the data. That is the honest model of most real pipelines: the
job maps and loads whatever it is given, and quality is a separate gate. Injected
defects therefore flow through to the warehouse, where the checks catch them (or
do not).
"""

from __future__ import annotations

import re

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_iso_date(s) -> bool:
    if not isinstance(s, str) or not _DATE_RE.match(s):
        return False
    y, m, d = (int(x) for x in s.split("-"))
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return False
    return True


def is_valid_email(s) -> bool:
    return isinstance(s, str) and bool(_EMAIL_RE.match(s))


def compute_line_total(quantity, unit_price, *, bug: bool = False) -> float | None:
    """quantity * unit_price, rounded. The `bug` path adds instead of multiplying
    -- the injected computed-field defect."""
    if quantity is None or unit_price is None:
        return None
    try:
        if bug:
            return round(float(quantity) + float(unit_price), 2)
        return round(float(quantity) * float(unit_price), 2)
    except (TypeError, ValueError):
        return None


def transform(sources: dict, process_bug: str | None = None) -> list[dict]:
    """Join orders to customers and products, cast, and derive line_total.
    Returns the enriched rows to be loaded. Never raises on dirty data; never
    repairs it."""
    customers = {c["id"]: c for c in sources["customers"]}
    products = {p["id"]: p for p in sources["products"]}

    rows: list[dict] = []
    for i, o in enumerate(sources["orders"]):
        if process_bug == "D10" and i % 8 == 0:
            continue                              # silent-drop bug: skip ~12% of rows

        cust = customers.get(o.get("customer_id"))
        prod = products.get(o.get("product_id"))
        rows.append({
            "order_id": o.get("id"),
            "customer_id": o.get("customer_id"),
            "customer_name": cust["name"] if cust else None,
            "country": cust["country"] if cust else None,
            "product_id": o.get("product_id"),
            "product_name": prod["name"] if prod else None,
            "category": prod["category"] if prod else None,
            "quantity": o.get("quantity"),
            "unit_price": o.get("unit_price"),
            "line_total": compute_line_total(o.get("quantity"), o.get("unit_price"),
                                             bug=(process_bug == "D09")),
            "order_date": o.get("order_date"),
            "email": cust["email"] if cust else None,
        })
    return rows
