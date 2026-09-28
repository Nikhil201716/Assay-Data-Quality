"""Distribution checks: the mean and spread of a numeric column against a
known-good baseline profile. This is the drift/anomaly gate -- it catches a scale
error or distribution shift where every individual row is still a valid number and
passes the per-row range check. It is the tool you reach for when you are
monitoring for drift and have no source-of-truth sum to reconcile against."""

from __future__ import annotations

import statistics

MEAN_TOL_FRAC = 0.30   # mean within +/-30% of baseline
STD_TOL_FRAC = 0.60    # std within +/-60% of baseline


def check(ctx) -> list[str]:
    v: list[str] = []
    prices = [r["unit_price"] for r in ctx.loaded if isinstance(r["unit_price"], (int, float))]
    if not prices:
        return v

    mean = statistics.fmean(prices)
    std = statistics.pstdev(prices)
    base_mean = ctx.profile["unit_price_mean"]
    base_std = ctx.profile["unit_price_std"]

    if abs(mean - base_mean) > MEAN_TOL_FRAC * base_mean:
        v.append(f"distribution: unit_price mean {mean:.2f} drifted from baseline {base_mean:.2f}")
    if abs(std - base_std) > STD_TOL_FRAC * max(base_std, 1e-9):
        v.append(f"distribution: unit_price spread {std:.2f} drifted from baseline {base_std:.2f}")
    return v
