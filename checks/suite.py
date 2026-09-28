"""Run every data-quality mechanism against a context and report which flagged.

The mechanisms, cheapest first:
    pipeline_ran   -- the trivial baseline: did the ETL job even complete? (A job
                      that loads garbage still 'succeeds', so this catches almost
                      nothing -- which is the point.)
    schema         -- required columns present and typed
    expectations   -- column-level value rules (the GE-style workhorse)
    referential    -- foreign keys resolve
    reconciliation -- counts, aggregate sum, idempotency vs source of truth
    distribution   -- numeric drift vs a known-good baseline profile
"""

from __future__ import annotations

from . import distribution, expectations, referential, reconciliation, schema

MECHANISMS = ["pipeline_ran", "schema", "expectations", "referential",
              "reconciliation", "distribution"]


def run(ctx) -> dict:
    return {
        "pipeline_ran": not ctx.ran_ok,        # only 'catches' if the job crashed
        "schema": bool(schema.check(ctx)),
        "expectations": bool(expectations.check(ctx)),
        "referential": bool(referential.check(ctx)),
        "reconciliation": bool(reconciliation.check(ctx)),
        "distribution": bool(distribution.check(ctx)),
    }


def violations(ctx) -> dict:
    """The actual violation messages per mechanism (for tests and debugging)."""
    return {
        "schema": schema.check(ctx),
        "expectations": expectations.check(ctx),
        "referential": referential.check(ctx),
        "reconciliation": reconciliation.check(ctx),
        "distribution": distribution.check(ctx),
    }
