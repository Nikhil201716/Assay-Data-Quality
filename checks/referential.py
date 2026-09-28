"""Referential integrity: every foreign key in the warehouse resolves to a real
row in the source lookup tables. Per-row value checks cannot see an orphaned
key; this check exists precisely to catch it."""

from __future__ import annotations


def check(ctx) -> list[str]:
    v: list[str] = []
    customer_ids = {c["id"] for c in ctx.sources["customers"]}
    product_ids = {p["id"] for p in ctx.sources["products"]}
    for r in ctx.loaded:
        if r.get("customer_id") not in customer_ids:
            v.append("referential: order.customer_id has no matching customer")
        if r.get("product_id") not in product_ids:
            v.append("referential: order.product_id has no matching product")
    return list(dict.fromkeys(v))
