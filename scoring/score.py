"""Scoring harness -- measures which data-quality check catches which defect.

For the clean data and for every defect in the catalog, it builds the (possibly
injected) sources, runs the ETL twice into one warehouse (so idempotency can be
judged), and runs every check mechanism, recording what each flagged. Defects
should be caught by at least one mechanism; the non-defect additive change by
none. Everything is seeded and in-process, so reports/*.json are reproducible.

    python scoring/score.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPORTS = ROOT / "reports"

from checks import suite                         # noqa: E402
from checks.context import Context, build_profile  # noqa: E402
from pipeline.generate import generate           # noqa: E402
from pipeline.load import connect                # noqa: E402
from pipeline.run_etl import run                 # noqa: E402
from scoring.defects import CATALOG, inject_data, is_process  # noqa: E402


def run_defect(defect_id, profile) -> Context:
    sources = inject_data(generate(), defect_id)
    pbug = is_process(defect_id)
    ran_ok = True
    try:
        conn = connect()
        loaded1, _ = run(sources, pbug, conn)
        loaded2, _ = run(sources, pbug, conn)     # second load into the same store
    except Exception:
        ran_ok, loaded1, loaded2 = False, [], []
    return Context(loaded=loaded1, loaded_again=loaded2, sources=sources,
                   ran_ok=ran_ok, profile=profile)


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    clean_loaded, _ = run(generate())
    profile = build_profile(clean_loaded)

    clean = suite.run(run_defect(None, profile))
    if any(clean.values()):
        raise RuntimeError(f"clean data is flagged by {clean} -- fix before scoring")
    print("clean: all checks green")

    matrix = {}
    for d in CATALOG:
        caught = suite.run(run_defect(d.id, profile))
        matrix[d.id] = {"klass": d.klass, "is_defect": d.is_defect,
                        "desc": d.desc, "caught": caught}
        marks = " ".join(f"{m[:4]}={'Y' if caught[m] else '.'}" for m in suite.MECHANISMS)
        tag = ""
        if d.is_defect and not any(caught.values()):
            tag = "MISSED"
        if (not d.is_defect) and any(caught.values()):
            tag = "FALSE POSITIVE"
        print(f"  {d.id} {d.klass:18s} {marks}  {tag}")

    mechs = suite.MECHANISMS
    defects = [k for k, m in matrix.items() if m["is_defect"]]
    additive = [k for k, m in matrix.items() if not m["is_defect"]]

    def caught_by(did, mech):
        return matrix[did]["caught"][mech]

    per_mech = {m: sum(1 for d in defects if caught_by(d, m)) for m in mechs}
    caught_any = [d for d in defects if any(matrix[d]["caught"].values())]
    missed = [d for d in defects if not any(matrix[d]["caught"].values())]
    false_pos = [d for d in additive if any(matrix[d]["caught"].values())]

    recon_only = [d for d in defects
                  if caught_by(d, "reconciliation") and not caught_by(d, "expectations")]
    dist_vs_exp = [d for d in defects
                   if caught_by(d, "distribution") and not caught_by(d, "expectations")]
    ref_only = [d for d in defects
                if caught_by(d, "referential") and not caught_by(d, "expectations")]

    classes = sorted({m["klass"] for m in matrix.values()})
    per_class = {k: {"defects": sum(1 for d in matrix if matrix[d]["klass"] == k),
                     **{m: sum(1 for d in matrix if matrix[d]["klass"] == k
                        and matrix[d]["caught"][m]) for m in mechs}}
                 for k in classes}

    summary = {
        "total_defects": len(defects),
        "additive_changes": len(additive),
        "mechanisms": mechs,
        "baseline_pipeline_ran_caught": per_mech["pipeline_ran"],
        "caught_per_mechanism": per_mech,
        "defects_caught_by_any": len(caught_any),
        "defects_missed_by_all": len(missed),
        "missed_defects": [{"id": d, "klass": matrix[d]["klass"], "desc": matrix[d]["desc"]}
                           for d in missed],
        "false_positives": [{"id": d, "klass": matrix[d]["klass"]} for d in false_pos],
        "reconciliation_catches_expectations_miss": recon_only,
        "distribution_catches_expectations_miss": dist_vs_exp,
        "referential_catches_expectations_miss": ref_only,
        "per_class": per_class,
        "headline": (
            f"'The pipeline ran' catches {per_mech['pipeline_ran']} of {len(defects)} "
            f"injected data defects. The expectation suite catches "
            f"{per_mech['expectations']}, reconciliation {per_mech['reconciliation']}, "
            f"referential {per_mech['referential']}, distribution "
            f"{per_mech['distribution']}; {len(missed)} slip past every check. "
            f"No check flagged the {len(additive)} additive change "
            f"({len(false_pos)} false positives)."),
    }

    (REPORTS / "catch_matrix.json").write_text(
        json.dumps({"defects": matrix}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPORTS / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("\n" + summary["headline"])
    print("wrote reports/catch_matrix.json, summary.json")


if __name__ == "__main__":
    main()
