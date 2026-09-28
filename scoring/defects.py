"""The defect catalog: realistic data-quality defects, injected one at a time.

Each defect is either a DATA defect (mutates the source tables) or a PROCESS
defect (a bug in the transform/load), plus one non-defect additive change used as
a false-positive probe. `is_defect=True` entries should be caught by at least one
check; the non-defect entry should be caught by none.

The point of the study is to measure which data-quality check catches which class
of defect -- so the injector is explicit, documented, and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Defect:
    id: str
    klass: str
    kind: str          # "data" | "process" | "none"
    is_defect: bool
    desc: str


CATALOG: list[Defect] = [
    Defect("D01", "null-required", "data", True,
           "customer_id is null on some orders (a required field)."),
    Defect("D02", "duplicate-key", "data", True,
           "a duplicate order id is present."),
    Defect("D03", "referential", "data", True,
           "some orders reference a customer_id that does not exist."),
    Defect("D04", "out-of-range", "data", True,
           "some order quantities are 0 or absurdly large."),
    Defect("D05", "out-of-range", "data", True,
           "some unit_prices are negative."),
    Defect("D06", "type-format", "data", True,
           "some order_date values are not valid ISO dates."),
    Defect("D07", "format-regex", "data", True,
           "some customer emails are malformed."),
    Defect("D08", "domain-set", "data", True,
           "some customer countries are outside the known set."),
    Defect("D11", "scale-error", "data", True,
           "every unit_price is inflated 100x (cents loaded as dollars)."),
    Defect("D13", "silent-corruption", "data", True,
           "some customer countries are changed to a DIFFERENT valid country."),
    Defect("D14", "encoding", "data", True,
           "some customer names are mojibake from a bad encoding."),
    Defect("D09", "computed-field", "process", True,
           "line_total is computed wrong (adds instead of multiplies)."),
    Defect("D10", "silent-drop", "process", True,
           "the transform silently drops ~12% of valid rows."),
    Defect("D12", "idempotency", "process", True,
           "the load appends instead of replacing (re-running doubles rows)."),
    Defect("D15", "additive", "none", False,
           "new products are added to the catalog that no order references "
           "(additive, non-defect)."),
]


def by_id(did: str) -> Defect:
    for d in CATALOG:
        if d.id == did:
            return d
    raise KeyError(did)


# ---- data defect injection ------------------------------------------------

def inject_data(sources: dict, defect_id: str | None) -> dict:
    """Mutate `sources` in place to introduce the given DATA (or none) defect.
    Process defects are handled in run_etl and leave the data untouched."""
    if defect_id is None:
        return sources
    d = by_id(defect_id)
    if d.kind not in ("data", "none"):
        return sources

    orders = sources["orders"]
    customers = sources["customers"]

    if defect_id == "D01":
        for o in orders[:15]:
            o["customer_id"] = None
    elif defect_id == "D02":
        dup = dict(orders[0])
        orders.append(dup)                       # same id as orders[0]
    elif defect_id == "D03":
        for o in orders[:12]:
            o["customer_id"] = 99999             # no such customer
    elif defect_id == "D04":
        for o in orders[:6]:
            o["quantity"] = 0
        for o in orders[6:12]:
            o["quantity"] = 100000
    elif defect_id == "D05":
        for o in orders[:10]:
            o["unit_price"] = -abs(o["unit_price"])
    elif defect_id == "D06":
        for o in orders[:8]:
            o["order_date"] = "31/13/2026"       # not ISO, not a real date
    elif defect_id == "D07":
        for c in customers[:5]:
            c["email"] = "not-an-email"
    elif defect_id == "D08":
        for c in customers[:5]:
            c["country"] = "ZZ"                  # not in the known set
    elif defect_id == "D11":
        for o in orders:
            o["unit_price"] = round(o["unit_price"] * 100, 2)
    elif defect_id == "D13":
        # valid -> different-but-valid country: individually plausible, wrong
        for c in customers[:10]:
            c["country"] = "FR" if c["country"] != "FR" else "US"
    elif defect_id == "D14":
        for c in customers[:6]:
            c["name"] = "Ã©tienne Ã¼ber"         # mojibake, still a non-null string
    elif defect_id == "D15":
        base = len(sources["products"])
        for k in range(1, 6):                    # new catalog products, unreferenced
            sources["products"].append({
                "id": base + k, "name": f"New Product {base + k}",
                "category": "books", "price": 42.0})
    return sources


def is_process(defect_id: str | None) -> str | None:
    """Return the process-bug name if this defect is a process defect, else None."""
    if defect_id is None:
        return None
    d = by_id(defect_id)
    return defect_id if d.kind == "process" else None
