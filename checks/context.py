"""The context every check reads: the loaded warehouse rows, the source tables,
a re-run of the load (for idempotency), whether the pipeline completed, and a
profile of the known-good data to reconcile against."""

from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass
class Context:
    loaded: list[dict]          # warehouse rows after one ETL run
    loaded_again: list[dict]    # warehouse rows after a second run into the same store
    sources: dict               # the (possibly defect-injected) source tables
    ran_ok: bool                # did the pipeline complete without raising
    profile: dict               # known-good baseline: count, sum, mean, std


def build_profile(clean_loaded: list[dict]) -> dict:
    prices = [r["unit_price"] for r in clean_loaded if isinstance(r["unit_price"], (int, float))]
    totals = [r["line_total"] for r in clean_loaded if isinstance(r["line_total"], (int, float))]
    return {
        "count": len(clean_loaded),
        "line_total_sum": round(sum(totals), 2),
        "unit_price_mean": statistics.fmean(prices),
        "unit_price_std": statistics.pstdev(prices),
    }
