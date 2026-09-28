"""Reconciliation against the known-good source of truth: row count, an aggregate
sum, and idempotency. These are aggregate checks -- they catch silent row drops,
duplicates, scale errors and non-idempotent loads that per-row checks miss, but
they are blind to which rows or which values are wrong."""

from __future__ import annotations

COUNT_TOL = 0          # exact
SUM_TOL_FRAC = 0.001   # 0.1% of the expected total


def check(ctx) -> list[str]:
    v: list[str] = []
    exp = ctx.profile

    if abs(len(ctx.loaded) - exp["count"]) > COUNT_TOL:
        v.append(f"reconciliation: row count {len(ctx.loaded)} != expected {exp['count']}")

    totals = [r["line_total"] for r in ctx.loaded if isinstance(r["line_total"], (int, float))]
    got = round(sum(totals), 2)
    if abs(got - exp["line_total_sum"]) > max(1.0, SUM_TOL_FRAC * abs(exp["line_total_sum"])):
        v.append(f"reconciliation: line_total sum {got} != expected {exp['line_total_sum']}")

    # idempotency: a second load into the same store must not change the row count
    if len(ctx.loaded_again) != len(ctx.loaded):
        v.append(f"reconciliation: not idempotent (re-run gives {len(ctx.loaded_again)} "
                 f"rows vs {len(ctx.loaded)})")

    return v
