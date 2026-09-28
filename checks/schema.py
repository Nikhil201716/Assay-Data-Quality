"""Schema checks: every warehouse row has the required columns, correctly typed
and non-null where required. This is the structural gate -- it catches missing or
mistyped fields, and is blind to whether the values themselves are sensible."""

from __future__ import annotations

REQUIRED_INT = ["order_id", "customer_id", "quantity"]
REQUIRED_NUM = ["unit_price", "line_total"]
REQUIRED_STR = ["order_date"]


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check(ctx) -> list[str]:
    v: list[str] = []
    for r in ctx.loaded:
        for c in REQUIRED_INT:
            if r.get(c) is None:
                v.append(f"schema: {c} is null")
            elif not _is_int(r[c]):
                v.append(f"schema: {c} is not an int")
        for c in REQUIRED_NUM:
            if r.get(c) is None:
                v.append(f"schema: {c} is null")
            elif not _is_num(r[c]):
                v.append(f"schema: {c} is not numeric")
        for c in REQUIRED_STR:
            if not isinstance(r.get(c), str):
                v.append(f"schema: {c} is not a string")
    return list(dict.fromkeys(v))
