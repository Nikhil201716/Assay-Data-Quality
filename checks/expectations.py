"""A Great-Expectations-style expectation suite: column-level value rules on the
warehouse. This is the workhorse of data-quality testing -- not-null, unique,
between, in-set, matches-regex, and a computed-field consistency check. It is
blind to defects where every row is individually valid (a valid-but-wrong value,
a silent row drop) -- exactly the gaps the other checks and the study expose.

The vocabulary mirrors GE on purpose: expect_column_values_to_not_be_null,
_to_be_unique, _to_be_between, _to_be_in_set, _to_match_regex.
"""

from __future__ import annotations

from pipeline.generate import COUNTRIES
from pipeline.transform import compute_line_total, is_iso_date, is_valid_email

VALID_COUNTRIES = set(COUNTRIES)


def check(ctx) -> list[str]:
    v: list[str] = []
    rows = ctx.loaded

    # not-null
    for r in rows:
        if r.get("order_id") is None:
            v.append("expect order_id not null")
        if r.get("customer_id") is None:
            v.append("expect customer_id not null")

    # unique order_id
    ids = [r.get("order_id") for r in rows]
    if len(ids) != len(set(ids)):
        v.append("expect order_id unique")

    for r in rows:
        q = r.get("quantity")
        if not (isinstance(q, (int, float)) and 1 <= q <= 100):
            v.append("expect quantity between 1 and 100")
        up = r.get("unit_price")
        if not (isinstance(up, (int, float)) and 0.01 <= up <= 1_000_000):
            v.append("expect unit_price between 0.01 and 1e6")
        if not is_iso_date(r.get("order_date")):
            v.append("expect order_date to be a valid ISO date")
        if r.get("email") is not None and not is_valid_email(r.get("email")):
            v.append("expect email to match the email pattern")
        if r.get("country") is not None and r.get("country") not in VALID_COUNTRIES:
            v.append("expect country in the known set")
        # computed-field consistency: line_total == quantity * unit_price
        expected = compute_line_total(q, up)
        if expected is not None and r.get("line_total") is not None:
            if abs(r["line_total"] - expected) > 0.01:
                v.append("expect line_total == quantity * unit_price")

    return list(dict.fromkeys(v))
